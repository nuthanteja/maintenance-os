from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PMOS_",
        extra="ignore",
        protected_namespaces=(),
    )

    predictor_id: str = "minirocket"
    predictor_path: Path = Path("models/minirocket_pipeline.joblib")

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8000", "http://127.0.0.1:8000"]
    )

    log_level: str = "INFO"

    ingestor: Literal["synthetic", "replay", "serial"] = "synthetic"
    replay_path: Path = Path("data/samples/replay.jsonl")
    replay_realtime: bool = True
    replay_loop: bool = True
    serial_port: str = "COM3"
    serial_baudrate: int = 921_600
    default_rpm: float = 2700.0
    triplet_max_age_s: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
