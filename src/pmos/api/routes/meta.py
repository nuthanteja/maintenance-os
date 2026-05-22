from fastapi import APIRouter, Depends

from ...inference.iso import ISO_ZONE_LABELS
from ...inference.service import PredictionService
from ..deps import get_prediction_service

router = APIRouter(tags=["meta"], prefix="/api")


@router.get("/meta")
def meta(svc: PredictionService = Depends(get_prediction_service)) -> dict:
    pred = svc.predictor
    return {
        "model_id": pred.model_id,
        "state_classes": pred.state_classes,
        "severity_classes": pred.severity_classes,
        "iso_zones": {z.value: label for z, label in ISO_ZONE_LABELS.items()},
        "input_contract": {
            "tensor_shape": [3, 1024],
            "axes": ["X", "Y", "Z"],
            "sample_rate_hz": 50000,
            "rpm_required": True,
        },
    }
