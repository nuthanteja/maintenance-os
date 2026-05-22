from pathlib import Path

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def joblib_path(project_root: Path) -> Path:
    p = project_root / "models" / "minirocket_pipeline.joblib"
    if not p.exists():
        pytest.skip(f"joblib bundle not found at {p}")
    return p


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(seed=42)


@pytest.fixture
def synthetic_window(rng: np.random.Generator) -> np.ndarray:
    """Random (3, 1024) tensor that mimics DC-removed sensor data."""
    return (rng.standard_normal((3, 1024)) * 1e6).astype(np.float64)
