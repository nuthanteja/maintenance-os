from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from numpy.typing import NDArray

from ..core.schemas import Prediction
from ..inference.iso import severity_to_zone
from .base import Predictor


class MiniRocketPredictor(Predictor):
    """Wraps the MiniRocket + dual RidgeClassifierCV bundle from the source notebook.

    Expected bundle keys:
        minirocket       — sktime MiniRocketMultivariate (already fit)
        clf_state        — RidgeClassifierCV for machine state
        clf_sev          — RidgeClassifierCV for severity
        speed_scaler     — MinMaxScaler fit on RPM integers
        encoder_state    — LabelEncoder for state classes
        encoder_sev      — LabelEncoder for severity classes
        global_max       — float, used to scale raw tensors before transform
    """

    EXPECTED_KEYS = {
        "minirocket",
        "clf_state",
        "clf_sev",
        "speed_scaler",
        "encoder_state",
        "encoder_sev",
        "global_max",
    }

    def __init__(self, bundle_path: Path | str) -> None:
        self._bundle_path = Path(bundle_path)
        if not self._bundle_path.exists():
            raise FileNotFoundError(f"joblib bundle not found at {self._bundle_path}")

        bundle = joblib.load(self._bundle_path)
        missing = self.EXPECTED_KEYS - set(bundle.keys())
        if missing:
            raise ValueError(f"joblib bundle missing keys: {sorted(missing)}")

        self._minirocket = bundle["minirocket"]
        self._clf_state = bundle["clf_state"]
        self._clf_sev = bundle["clf_sev"]
        self._speed_scaler = bundle["speed_scaler"]
        self._encoder_state = bundle["encoder_state"]
        self._encoder_sev = bundle["encoder_sev"]
        self._global_max = float(bundle["global_max"])

    @property
    def model_id(self) -> str:
        return "minirocket"

    @property
    def state_classes(self) -> list[str]:
        return [str(c) for c in self._encoder_state.classes_]

    @property
    def severity_classes(self) -> list[str]:
        return [str(c) for c in self._encoder_sev.classes_]

    def predict(self, tensor: NDArray, rpm: float) -> Prediction:
        if tensor.ndim != 2 or tensor.shape != (3, 1024):
            raise ValueError(f"expected tensor of shape (3, 1024), got {tensor.shape}")

        scaled = (tensor / self._global_max).astype(np.float32)
        sktime_input = scaled[np.newaxis, ...]
        features = np.asarray(self._minirocket.transform(sktime_input))

        # Match the column name the scaler was fit with in the source notebook
        # ("motor_speed_int"); avoids sklearn's "no feature names" UserWarning.
        rpm_df = pd.DataFrame([[float(rpm)]], columns=["motor_speed_int"])
        rpm_norm = self._speed_scaler.transform(rpm_df)
        fused = np.hstack([features, rpm_norm])

        state_idx, state_conf = _predict_with_confidence(self._clf_state, fused)
        sev_idx, sev_conf = _predict_with_confidence(self._clf_sev, fused)

        state_label = self._encoder_state.inverse_transform([state_idx])[0]
        sev_label = self._encoder_sev.inverse_transform([sev_idx])[0]
        zone, zone_label = severity_to_zone(str(sev_label))

        return Prediction(
            state=str(state_label),
            state_confidence=float(state_conf),
            severity=str(sev_label),
            severity_confidence=float(sev_conf),
            iso_zone=zone.value,
            iso_zone_label=zone_label,
            rpm=float(rpm),
            model_id=self.model_id,
        )


def _predict_with_confidence(clf, X: NDArray) -> tuple[int, float]:
    margins = np.asarray(clf.decision_function(X))

    if margins.ndim == 1:
        m = float(margins[0])
        idx = 1 if m >= 0 else 0
        conf = 1.0 / (1.0 + np.exp(-abs(m)))
        return idx, float(conf)

    row = margins[0]
    probs = _softmax(row)
    idx = int(np.argmax(probs))
    return idx, float(probs[idx])


def _softmax(z: NDArray) -> NDArray:
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()
