"""SerialIngestor — reads ASCII-hex frames from the real sensor over UART.

Mirrors the wire protocol used by `MMS_Scripts/get_data_wave_uart.py`:
each line is `<device_id> <axis> <hex_s0> ... <hex_s1023>\\n` with samples
as 32-bit unsigned ints in hex. DC removal happens here on the host."""
import asyncio
import logging
import time
from typing import AsyncIterator

import numpy as np

from .events import AxisEvent
from .ingestor import BaseIngestor

logger = logging.getLogger(__name__)

_EXPECTED_SAMPLES = 1024
_EXPECTED_PARTS = _EXPECTED_SAMPLES + 2  # device_id + axis + 1024 hex tokens


class SerialIngestor(BaseIngestor):
    def __init__(
        self,
        port: str,
        baudrate: int = 921_600,
        *,
        read_timeout_s: float = 3.0,
    ) -> None:
        super().__init__()
        self._port = port
        self._baudrate = baudrate
        self._read_timeout_s = read_timeout_s
        self._serial = None  # opened lazily so import-time doesn't require pyserial

    async def events(self) -> AsyncIterator[AxisEvent]:
        import serial  # lazy import — only needed when this ingestor runs

        self._serial = serial.Serial(self._port, self._baudrate, timeout=self._read_timeout_s)
        try:
            self._serial.set_buffer_size(rx_size=1_000_000, tx_size=1_000_000)
        except (AttributeError, NotImplementedError):
            pass  # set_buffer_size is Windows-only; non-fatal elsewhere
        self._serial.reset_input_buffer()
        logger.info("opened serial port %s @ %d baud", self._port, self._baudrate)

        while not self._stop.is_set():
            line_bytes = await asyncio.to_thread(self._serial.readline)
            if not line_bytes:
                continue
            try:
                line = line_bytes.decode(errors="ignore").strip()
                parts = line.split()
                if len(parts) < _EXPECTED_PARTS:
                    continue
                device_id = parts[0]
                axis = parts[1].upper()
                if axis not in ("X", "Y", "Z"):
                    continue
                wave = np.array(
                    [int(s, 16) for s in parts[2 : 2 + _EXPECTED_SAMPLES]],
                    dtype=np.uint32,
                )
            except (ValueError, UnicodeDecodeError) as e:
                logger.warning("serial parse error: %s", e)
                continue

            samples = wave.astype(np.float64) - wave.mean()
            yield AxisEvent(
                timestamp=time.time(),
                axis=axis,
                samples=samples,
                device_id=device_id,
            )

    async def aclose(self) -> None:
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
            logger.info("closed serial port %s", self._port)
