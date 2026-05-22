"""JsonlReplayIngestor — replays a saved sensor JSONL file as a stream."""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import AsyncIterator

import numpy as np

from .events import AxisEvent
from .ingestor import BaseIngestor

logger = logging.getLogger(__name__)


class JsonlReplayIngestor(BaseIngestor):
    def __init__(
        self,
        path: Path | str,
        *,
        realtime: bool = True,
        loop: bool = True,
        device_id: str | None = None,
    ) -> None:
        super().__init__()
        self._path = Path(path)
        self._realtime = realtime
        self._loop = loop
        self._device_id = device_id

    async def events(self) -> AsyncIterator[AxisEvent]:
        records = self._load_all()
        if not records:
            logger.warning("replay file %s contains no usable records", self._path)
            return

        while not self._stop.is_set():
            wall_start = time.monotonic()
            stream_start = records[0][0]

            for orig_t, axis, data in records:
                if self._stop.is_set():
                    break
                if self._realtime:
                    target = wall_start + (orig_t - stream_start)
                    delay = target - time.monotonic()
                    if delay > 0:
                        try:
                            await asyncio.wait_for(self._stop.wait(), timeout=delay)
                            break  # stop signalled
                        except asyncio.TimeoutError:
                            pass
                yield AxisEvent(
                    timestamp=time.time(),
                    axis=axis,
                    samples=np.asarray(data, dtype=np.float64),
                    device_id=self._device_id,
                )

            if not self._loop:
                break

    def _load_all(self) -> list[tuple[float, str, list[float]]]:
        if not self._path.exists():
            raise FileNotFoundError(f"replay file not found: {self._path}")

        records: list[tuple[float, str, list[float]]] = []
        with self._path.open("r", encoding="utf-8") as f:
            for line_no, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("replay %s:%d skipped: invalid JSON", self._path, line_no)
                    continue
                axis = str(obj.get("axis", "")).strip().upper()
                data = obj.get("data")
                if axis not in ("X", "Y", "Z") or not isinstance(data, list) or len(data) != 1024:
                    continue
                records.append((float(obj.get("time", 0.0)), axis, data))

        records.sort(key=lambda r: r[0])
        return records
