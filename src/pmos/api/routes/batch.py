import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ...core.schemas import BatchPredictionResponse, PlotData
from ...inference.service import PredictionService
from ...pipeline.csv_loader import parse_csv
from ...pipeline.jsonl_loader import parse_jsonl
from ...pipeline.plots import DEFAULT_SAMPLE_RATE_HZ, build_plot_data
from ..deps import get_prediction_service

router = APIRouter(tags=["batch"], prefix="/api")


@router.post("/batch/predict", response_model=BatchPredictionResponse)
async def batch_predict(
    file: UploadFile = File(..., description="CSV (axis,s0..s1023 header) or sensor-native JSONL"),
    rpm: float = Form(..., gt=0, description="Motor speed in RPM"),
    svc: PredictionService = Depends(get_prediction_service),
) -> BatchPredictionResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="uploaded file is empty")

    try:
        tensor = _parse_by_filename(raw, file.filename)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    prediction = svc.predict(tensor, rpm=rpm)
    plot_data = build_plot_data(tensor, sample_rate_hz=DEFAULT_SAMPLE_RATE_HZ)

    return BatchPredictionResponse(
        prediction=prediction,
        plot_data=PlotData.model_validate(plot_data),
        sample_rate_hz=DEFAULT_SAMPLE_RATE_HZ,
    )


def _parse_by_filename(raw: bytes, filename: str | None):
    name = (filename or "").lower()
    if name.endswith(".jsonl") or name.endswith(".ndjson"):
        return parse_jsonl(raw)
    if name.endswith(".csv"):
        return parse_csv(raw)

    # Fallback: sniff by content. JSONL starts with `{` once whitespace is stripped.
    head = raw.lstrip()[:1]
    if head == b"{":
        return parse_jsonl(raw)
    return parse_csv(raw)
