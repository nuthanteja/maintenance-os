import json

import numpy as np
import pytest

from pmos.pipeline.jsonl_loader import parse_jsonl


def _line(time: float, axis: str, data) -> str:
    return json.dumps({"time": time, "axis": axis, "data": list(data)}) + "\n"


@pytest.fixture
def single_triplet(rng) -> str:
    return "".join(
        _line(1.0 + i * 0.02, ax, rng.standard_normal(1024))
        for i, ax in enumerate(("X", "Y", "Z"))
    )


def test_parse_single_triplet(single_triplet):
    tensor = parse_jsonl(single_triplet)
    assert tensor.shape == (3, 1024)
    assert tensor.dtype == np.float64
    np.testing.assert_allclose(tensor.mean(axis=1), 0.0, atol=1e-10)


def test_picks_latest_window_per_axis(rng):
    early = [rng.standard_normal(1024) for _ in range(3)]
    late = [rng.standard_normal(1024) for _ in range(3)]

    lines = []
    for i, ax in enumerate(("X", "Y", "Z")):
        lines.append(_line(1.0, ax, early[i]))
        lines.append(_line(5.0, ax, late[i]))
    content = "".join(lines)

    tensor = parse_jsonl(content)
    for i in range(3):
        np.testing.assert_allclose(tensor[i], late[i] - late[i].mean())


def test_skips_blank_lines(rng):
    content = (
        "\n"
        + _line(1.0, "X", rng.standard_normal(1024))
        + "\n\n"
        + _line(1.02, "Y", rng.standard_normal(1024))
        + _line(1.04, "Z", rng.standard_normal(1024))
        + "\n"
    )
    tensor = parse_jsonl(content)
    assert tensor.shape == (3, 1024)


def test_rejects_missing_axis():
    content = _line(1.0, "X", [0.0] * 1024) + _line(1.02, "Y", [0.0] * 1024)
    with pytest.raises(ValueError, match="missing axes"):
        parse_jsonl(content)


def test_rejects_wrong_sample_count():
    content = _line(1.0, "X", [0.0] * 512)
    with pytest.raises(ValueError, match="expected 1024"):
        parse_jsonl(content)


def test_rejects_invalid_json():
    content = "{not valid json}\n"
    with pytest.raises(ValueError, match="invalid JSON"):
        parse_jsonl(content)


def test_ignores_unknown_axis(rng):
    content = (
        _line(1.0, "W", [0.0] * 1024)
        + _line(1.02, "X", rng.standard_normal(1024))
        + _line(1.04, "Y", rng.standard_normal(1024))
        + _line(1.06, "Z", rng.standard_normal(1024))
    )
    tensor = parse_jsonl(content)
    assert tensor.shape == (3, 1024)
