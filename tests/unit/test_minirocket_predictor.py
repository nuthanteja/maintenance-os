import numpy as np
import pytest

from pmos.core.schemas import Prediction
from pmos.models.minirocket import MiniRocketPredictor


@pytest.fixture(scope="module")
def predictor(joblib_path):
    return MiniRocketPredictor(joblib_path)


def test_classes_loaded(predictor):
    assert len(predictor.state_classes) >= 2
    assert sorted(predictor.severity_classes) == sorted(
        ["baseline", "low", "medium", "high"]
    )


def test_predict_returns_prediction_schema(predictor, synthetic_window):
    pred = predictor.predict(synthetic_window, rpm=2700)
    assert isinstance(pred, Prediction)
    assert pred.state in predictor.state_classes
    assert pred.severity in predictor.severity_classes
    assert 0.0 <= pred.state_confidence <= 1.0
    assert 0.0 <= pred.severity_confidence <= 1.0
    assert pred.iso_zone in {"A", "B", "C", "D"}
    assert pred.rpm == 2700.0
    assert pred.model_id == "minirocket"


def test_predict_rejects_wrong_shape(predictor):
    with pytest.raises(ValueError):
        predictor.predict(np.zeros((2, 1024)), rpm=2700)
    with pytest.raises(ValueError):
        predictor.predict(np.zeros((3, 1023)), rpm=2700)


def test_iso_zone_consistency(predictor, synthetic_window):
    pred = predictor.predict(synthetic_window, rpm=2700)
    expected = {"baseline": "A", "low": "B", "medium": "C", "high": "D"}
    assert pred.iso_zone == expected[pred.severity]
