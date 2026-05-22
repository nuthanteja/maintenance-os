import time

import pytest
from fastapi.testclient import TestClient

from pmos.api.app import create_app
from pmos.streaming.manager import reset_stream_manager


@pytest.fixture(scope="module")
def stream_client(joblib_path, monkeypatch_module):
    monkeypatch_module.setenv("PMOS_INGESTOR", "synthetic")
    reset_stream_manager()
    # Force a fresh settings cache so the env override is picked up.
    from pmos.config import get_settings

    get_settings.cache_clear()
    from pmos.api.deps import get_prediction_service

    get_prediction_service.cache_clear()

    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


def test_ws_emits_prediction_frames(stream_client):
    deadline = time.time() + 10.0
    with stream_client.websocket_connect("/ws/stream") as ws:
        seen_status = False
        seen_prediction = False
        seen_plot = False
        while time.time() < deadline and not (seen_prediction and seen_plot):
            msg = ws.receive_json()
            mtype = msg.get("type")
            if mtype == "status":
                seen_status = True
            elif mtype == "prediction":
                frame = msg["frame"]
                assert frame["model_id"] == "minirocket"
                assert frame["iso_zone"] in {"A", "B", "C", "D"}
                assert 0.0 <= frame["state_confidence"] <= 1.0
                seen_prediction = True
            elif mtype == "plot":
                assert "data" in msg
                assert len(msg["data"]["time_domain"]["X"]) == 1024
                seen_plot = True
        assert seen_status
        assert seen_prediction
        assert seen_plot


def test_ws_eco_mode_suppresses_plots(stream_client):
    deadline = time.time() + 10.0
    with stream_client.websocket_connect("/ws/stream") as ws:
        ws.send_json({"type": "set_eco", "eco": True})

        prediction_count = 0
        plot_count = 0
        while time.time() < deadline and prediction_count < 3:
            msg = ws.receive_json()
            mtype = msg.get("type")
            if mtype == "prediction":
                prediction_count += 1
            elif mtype == "plot":
                plot_count += 1

        assert prediction_count >= 3
        assert plot_count == 0


def test_ws_ping(stream_client):
    with stream_client.websocket_connect("/ws/stream") as ws:
        # Drain the initial status message
        first = ws.receive_json()
        assert first["type"] == "status"

        ws.send_json({"type": "ping"})
        for _ in range(20):
            msg = ws.receive_json()
            if msg.get("type") == "pong":
                return
        pytest.fail("did not receive pong")
