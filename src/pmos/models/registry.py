from pathlib import Path
from typing import Callable

from .base import Predictor
from .minirocket import MiniRocketPredictor


_REGISTRY: dict[str, Callable[..., Predictor]] = {
    "minirocket": MiniRocketPredictor,
}


def get_predictor(predictor_id: str, model_path: Path | str) -> Predictor:
    if predictor_id not in _REGISTRY:
        raise KeyError(
            f"Unknown predictor id: {predictor_id!r}. Known: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[predictor_id](model_path)


def register(predictor_id: str, factory: Callable[..., Predictor]) -> None:
    _REGISTRY[predictor_id] = factory
