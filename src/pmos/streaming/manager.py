import asyncio
import logging
from typing import Any

from fastapi import WebSocket

from ..core.schemas import PredictionFrame
from ..inference.service import PredictionService
from ..pipeline.plots import build_plot_data
from .buffer import TripletBuffer
from .ingestor import BaseIngestor

logger = logging.getLogger(__name__)


class StreamClient:
    __slots__ = ("ws", "eco_mode")

    def __init__(self, ws: WebSocket, eco_mode: bool = False) -> None:
        self.ws = ws
        self.eco_mode = eco_mode

    async def send_json(self, payload: dict) -> None:
        await self.ws.send_json(payload)


class StreamManager:
    """Owns the active ingestor, a single shared TripletBuffer, the
    prediction loop, and the set of connected WebSocket clients."""

    def __init__(self) -> None:
        self._ingestor: BaseIngestor | None = None
        self._svc: PredictionService | None = None
        self._buffer: TripletBuffer | None = None
        self._task: asyncio.Task | None = None
        self._rpm: float = 2700.0
        self._clients: set[StreamClient] = set()
        self._lock = asyncio.Lock()

    def configure(
        self,
        ingestor: BaseIngestor,
        svc: PredictionService,
        *,
        rpm: float,
        triplet_max_age_s: float = 1.0,
    ) -> None:
        self._ingestor = ingestor
        self._svc = svc
        self._buffer = TripletBuffer(max_age_s=triplet_max_age_s)
        self._rpm = float(rpm)

    @property
    def configured(self) -> bool:
        return self._ingestor is not None and self._svc is not None

    @property
    def rpm(self) -> float:
        return self._rpm

    @property
    def ingestor_name(self) -> str:
        return type(self._ingestor).__name__ if self._ingestor else "none"

    async def start(self) -> None:
        if not self.configured:
            logger.warning("StreamManager.start() called without configure() — skipping")
            return
        self._task = asyncio.create_task(self._run(), name="stream-manager")

    async def stop(self) -> None:
        if self._ingestor is not None:
            await self._ingestor.stop()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        if self._ingestor is not None:
            await self._ingestor.aclose()

    async def add_client(self, client: StreamClient) -> None:
        async with self._lock:
            self._clients.add(client)
        await client.send_json(
            {
                "type": "status",
                "ingestor": self.ingestor_name,
                "rpm": self._rpm,
                "eco_mode": client.eco_mode,
            }
        )

    async def remove_client(self, client: StreamClient) -> None:
        async with self._lock:
            self._clients.discard(client)

    async def set_rpm(self, rpm: float) -> None:
        self._rpm = float(rpm)
        await self._broadcast({"type": "status", "rpm": self._rpm})

    async def _run(self) -> None:
        assert self._ingestor is not None
        assert self._svc is not None
        assert self._buffer is not None
        try:
            async for event in self._ingestor.events():
                triplet = self._buffer.push(event)
                if triplet is None:
                    continue
                try:
                    pred = await asyncio.to_thread(
                        self._svc.predict, triplet.tensor, self._rpm
                    )
                except Exception:
                    logger.exception("prediction failed")
                    continue

                frame = PredictionFrame(
                    **pred.model_dump(),
                    timestamp=triplet.timestamp,
                    device_id=triplet.device_id,
                )
                plot = build_plot_data(triplet.tensor)

                await self._broadcast(
                    {"type": "prediction", "frame": frame.model_dump()},
                    plot_payload={"type": "plot", "timestamp": triplet.timestamp, "data": plot},
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("stream manager loop crashed")

    async def _broadcast(self, payload: dict, *, plot_payload: dict | None = None) -> None:
        async with self._lock:
            clients = list(self._clients)
        for client in clients:
            try:
                await client.send_json(payload)
                if plot_payload is not None and not client.eco_mode:
                    await client.send_json(plot_payload)
            except Exception:
                logger.debug("client send failed; will be cleaned up on disconnect")


_singleton: StreamManager | None = None


def get_stream_manager() -> StreamManager:
    global _singleton
    if _singleton is None:
        _singleton = StreamManager()
    return _singleton


def reset_stream_manager() -> None:
    """Test helper — drops the singleton so a fresh one is built."""
    global _singleton
    _singleton = None
