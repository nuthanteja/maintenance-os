import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator

from .events import AxisEvent


class BaseIngestor(ABC):
    """Source of axis-window events. Implementations are async generators —
    consumers iterate via `async for event in ingestor.events()`.

    Implementations should respect `self._stop` (set via `await self.stop()`)
    and exit their event loop promptly. Cleanup of underlying resources
    (file handles, serial ports) goes in `aclose()`.
    """

    def __init__(self) -> None:
        self._stop = asyncio.Event()

    @abstractmethod
    def events(self) -> AsyncIterator[AxisEvent]: ...

    async def stop(self) -> None:
        self._stop.set()

    async def aclose(self) -> None:
        """Release underlying resources. Default no-op."""
