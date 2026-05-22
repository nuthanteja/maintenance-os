from functools import lru_cache

from ..config import get_settings
from ..inference.service import PredictionService
from ..models.registry import get_predictor
from ..streaming.ingestor import BaseIngestor
from ..streaming.manager import StreamManager, get_stream_manager
from ..streaming.replay import JsonlReplayIngestor
from ..streaming.serial_ingestor import SerialIngestor
from ..streaming.synthetic import SyntheticIngestor


@lru_cache
def get_prediction_service() -> PredictionService:
    settings = get_settings()
    predictor = get_predictor(settings.predictor_id, settings.predictor_path)
    return PredictionService(predictor)


def build_ingestor() -> BaseIngestor:
    settings = get_settings()
    match settings.ingestor:
        case "synthetic":
            return SyntheticIngestor()
        case "replay":
            return JsonlReplayIngestor(
                path=settings.replay_path,
                realtime=settings.replay_realtime,
                loop=settings.replay_loop,
            )
        case "serial":
            return SerialIngestor(
                port=settings.serial_port,
                baudrate=settings.serial_baudrate,
            )
        case other:
            raise ValueError(f"unknown PMOS_INGESTOR={other!r}")


__all__ = [
    "get_prediction_service",
    "get_stream_manager",
    "build_ingestor",
    "StreamManager",
]
