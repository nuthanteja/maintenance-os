from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class AxisEvent:
    timestamp: float
    axis: str
    samples: np.ndarray
    device_id: str | None = None


@dataclass(slots=True)
class Triplet:
    timestamp: float
    tensor: np.ndarray  # shape (3, 1024)
    device_id: str | None = None
