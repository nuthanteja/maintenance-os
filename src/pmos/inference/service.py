from numpy.typing import NDArray

from ..core.schemas import Prediction
from ..models.base import Predictor


class PredictionService:
    """Thin facade over a Predictor. Cross-cutting concerns (logging, metrics,
    request batching) will be layered here without touching model code."""

    def __init__(self, predictor: Predictor) -> None:
        self._predictor = predictor

    @property
    def predictor(self) -> Predictor:
        return self._predictor

    def predict(self, tensor: NDArray, rpm: float) -> Prediction:
        return self._predictor.predict(tensor, rpm)
