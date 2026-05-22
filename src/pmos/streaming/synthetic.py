"""SyntheticIngestor — emits sine+harmonics+noise windows so the realtime
pipeline is demoable without a sensor or saved JSONL file."""
import asyncio
import time
from typing import AsyncIterator

import numpy as np

from .events import AxisEvent
from .ingestor import BaseIngestor

_AXIS_BASE_FREQ_HZ = {"X": 100.0, "Y": 105.0, "Z": 95.0}
_AXIS_PHASE = {"X": 0.0, "Y": 1.1, "Z": 2.3}


class SyntheticIngestor(BaseIngestor):
    def __init__(
        self,
        *,
        sample_rate_hz: int = 50_000,
        n_samples: int = 1024,
        window_period_s: float = 0.05,
        noise_amplitude: float = 0.05,
        scale: float = 1e6,
        device_id: str = "SYNTH_001",
        seed: int | None = None,
    ) -> None:
        super().__init__()
        self._sample_rate_hz = sample_rate_hz
        self._n_samples = n_samples
        self._window_period_s = window_period_s
        self._noise_amp = noise_amplitude
        self._scale = scale
        self._device_id = device_id
        self._rng = np.random.default_rng(seed)

    async def events(self) -> AsyncIterator[AxisEvent]:
        t_phase = 0.0
        while not self._stop.is_set():
            for axis in ("X", "Y", "Z"):
                if self._stop.is_set():
                    break
                samples = self._make_window(axis, t_phase)
                yield AxisEvent(
                    timestamp=time.time(),
                    axis=axis,
                    samples=samples,
                    device_id=self._device_id,
                )
                try:
                    await asyncio.wait_for(
                        self._stop.wait(), timeout=self._window_period_s
                    )
                except asyncio.TimeoutError:
                    pass
            t_phase += self._n_samples / self._sample_rate_hz

    def _make_window(self, axis: str, t_phase: float) -> np.ndarray:
        n = self._n_samples
        t = t_phase + np.arange(n) / self._sample_rate_hz
        f0 = _AXIS_BASE_FREQ_HZ[axis]
        phi = _AXIS_PHASE[axis]
        sig = (
            np.sin(2 * np.pi * f0 * t + phi)
            + 0.3 * np.sin(2 * np.pi * 2 * f0 * t + phi)
            + 0.1 * np.sin(2 * np.pi * 5 * f0 * t + phi)
        )
        sig += self._noise_amp * self._rng.standard_normal(n)
        return (sig * self._scale).astype(np.float64)
