from pydantic import BaseModel, ConfigDict, Field


class Prediction(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    state: str = Field(..., description="Predicted machine state label")
    state_confidence: float = Field(..., ge=0.0, le=1.0)
    severity: str = Field(..., description="Predicted severity bucket")
    severity_confidence: float = Field(..., ge=0.0, le=1.0)
    iso_zone: str = Field(..., description="ISO 20816-3 zone code (A/B/C/D)")
    iso_zone_label: str
    rpm: float = Field(..., ge=0.0)
    model_id: str


class PredictionFrame(Prediction):
    timestamp: float = Field(..., description="Unix epoch seconds at prediction time")
    device_id: str | None = None


class TimeDomainPlot(BaseModel):
    time_s: list[float]
    X: list[float]
    Y: list[float]
    Z: list[float]


class SpectrumPlot(BaseModel):
    frequency_hz: list[float]
    X: list[float]
    Y: list[float]
    Z: list[float]


class AxisStats(BaseModel):
    X: float
    Y: float
    Z: float


class PlotStats(BaseModel):
    rms: AxisStats
    peak: AxisStats
    crest_factor: AxisStats
    kurtosis: AxisStats


class PlotData(BaseModel):
    time_domain: TimeDomainPlot
    frequency_domain: SpectrumPlot
    envelope_spectrum: SpectrumPlot
    stats: PlotStats


class BatchPredictionResponse(BaseModel):
    prediction: Prediction
    plot_data: PlotData
    sample_rate_hz: int = 50_000
