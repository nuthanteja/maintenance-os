import numpy as np
from numpy.typing import NDArray


def dc_remove(tensor: NDArray) -> NDArray:
    """Subtract the per-axis mean. Idempotent — safe to apply to already
    DC-removed sensor data (the mean of zero-mean data is ~0)."""
    return tensor - tensor.mean(axis=-1, keepdims=True)
