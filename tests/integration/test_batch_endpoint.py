import io
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from pmos.api.app import create_app


@pytest.fixture(scope="module")
def client(joblib_path):
    app = create_app()
    with TestClient(app) as c:
        yield c


def _csv_bytes(rng: np.random.Generator) -> bytes:
    header = ",".join(["axis"] + [f"s{i}" for i in range(1024)])
    rows = [header]
    for ax in ("X", "Y", "Z"):
        rows.append(ax + "," + ",".join(str(v) for v in rng.standard_normal(1024)))
    return ("\n".join(rows) + "\n").encode("utf-8")


def _jsonl_bytes(rng: np.random.Generator) -> bytes:
    lines = []
    for i, ax in enumerate(("X", "Y", "Z")):
        obj = {"time": 1.0 + i * 0.02, "axis": ax, "data": rng.standard_normal(1024).tolist()}
        lines.append(json.dumps(obj))
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_meta_returns_classes(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["model_id"] == "minirocket"
    assert sorted(body["severity_classes"]) == sorted(["baseline", "low", "medium", "high"])
    assert set(body["iso_zones"].keys()) == {"A", "B", "C", "D"}
    assert body["input_contract"]["tensor_shape"] == [3, 1024]


def test_batch_predict_csv(client, rng):
    files = {"file": ("sample.csv", io.BytesIO(_csv_bytes(rng)), "text/csv")}
    r = client.post("/api/batch/predict", files=files, data={"rpm": "2700"})
    assert r.status_code == 200, r.text
    body = r.json()

    pred = body["prediction"]
    assert pred["model_id"] == "minirocket"
    assert pred["iso_zone"] in {"A", "B", "C", "D"}
    assert 0.0 <= pred["state_confidence"] <= 1.0
    assert pred["rpm"] == 2700.0

    plot = body["plot_data"]
    assert len(plot["time_domain"]["X"]) == 1024
    assert len(plot["frequency_domain"]["frequency_hz"]) == 513  # rfft of N=1024
    assert len(plot["envelope_spectrum"]["frequency_hz"]) == 513
    for key in ("rms", "peak", "crest_factor", "kurtosis"):
        assert key in plot["stats"]
        assert {"X", "Y", "Z"} <= plot["stats"][key].keys()
    assert body["sample_rate_hz"] == 50_000


def test_batch_predict_jsonl(client, rng):
    files = {"file": ("sample.jsonl", io.BytesIO(_jsonl_bytes(rng)), "application/x-ndjson")}
    r = client.post("/api/batch/predict", files=files, data={"rpm": "2200"})
    assert r.status_code == 200, r.text
    assert r.json()["prediction"]["rpm"] == 2200.0


def test_batch_predict_rejects_empty_file(client):
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    r = client.post("/api/batch/predict", files=files, data={"rpm": "2700"})
    assert r.status_code == 422


def test_batch_predict_rejects_missing_rpm(client, rng):
    files = {"file": ("sample.csv", io.BytesIO(_csv_bytes(rng)), "text/csv")}
    r = client.post("/api/batch/predict", files=files)
    assert r.status_code == 422


def test_batch_predict_rejects_malformed_csv(client):
    files = {"file": ("bad.csv", io.BytesIO(b"not,a,valid,csv\n"), "text/csv")}
    r = client.post("/api/batch/predict", files=files, data={"rpm": "2700"})
    assert r.status_code == 422
