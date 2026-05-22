from abc import ABC, abstractmethod

from numpy.typing import NDArray

from ..core.schemas import Prediction


class Predictor(ABC):
    """Pluggable model interface. Implementations wrap a serialized bundle and
    return a normalized Prediction regardless of the underlying algorithm."""

    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @property
    @abstractmethod
    def state_classes(self) -> list[str]: ...

    @property
    @abstractmethod
    def severity_classes(self) -> list[str]: ...

    @abstractmethod
    def predict(self, tensor: NDArray, rpm: float) -> Prediction:
        """tensor: shape (3, 1024) — DC-removed waveforms in axis order (X, Y, Z).
        rpm: motor speed in revolutions per minute."""
