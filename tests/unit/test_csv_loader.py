import io

import numpy as np
import pytest

from pmos.pipeline.csv_loader import parse_csv


def _build_csv(rows: list[list]) -> str:
    buf = io.StringIO()
    for r in rows:
        buf.write(",".join(str(c) for c in r) + "\n")
    return buf.getvalue()


@pytest.fixture
def good_csv(rng) -> str:
    header = ["axis"] + [f"s{i}" for i in range(1024)]
    rows = [header]
    for axis in ("X", "Y", "Z"):
        rows.append([axis] + rng.standard_normal(1024).tolist())
    return _build_csv(rows)


def test_parse_returns_3x1024(good_csv):
    tensor = parse_csv(good_csv)
    assert tensor.shape == (3, 1024)
    assert tensor.dtype == np.float64


def test_parse_dc_removed(good_csv):
    tensor = parse_csv(good_csv)
    np.testing.assert_allclose(tensor.mean(axis=1), 0.0, atol=1e-10)


def test_parse_reorders_axes_to_xyz(rng):
    header = ["axis"] + [f"s{i}" for i in range(1024)]
    x = rng.standard_normal(1024)
    y = rng.standard_normal(1024)
    z = rng.standard_normal(1024)
    rows = [header, ["Z"] + z.tolist(), ["X"] + x.tolist(), ["Y"] + y.tolist()]
    tensor = parse_csv(_build_csv(rows))
    np.testing.assert_allclose(tensor[0], x - x.mean())
    np.testing.assert_allclose(tensor[1], y - y.mean())
    np.testing.assert_allclose(tensor[2], z - z.mean())


def test_rejects_missing_header():
    # 4 rows so the row-count check passes — first row's first cell isn't 'axis'.
    rows = [
        ["X"] + [0.0] * 1024,
        ["Y"] + [0.0] * 1024,
        ["Z"] + [0.0] * 1024,
        ["W"] + [0.0] * 1024,
    ]
    with pytest.raises(ValueError, match="first column must be 'axis'"):
        parse_csv(_build_csv(rows))


def test_rejects_wrong_sample_count():
    header = ["axis"] + [f"s{i}" for i in range(512)]
    rows = [header] + [[ax] + [0.0] * 512 for ax in ("X", "Y", "Z")]
    with pytest.raises(ValueError, match="expected 1024 sample columns"):
        parse_csv(_build_csv(rows))


def test_rejects_missing_axis():
    header = ["axis"] + [f"s{i}" for i in range(1024)]
    rows = [header, ["X"] + [0.0] * 1024, ["Y"] + [0.0] * 1024]
    with pytest.raises(ValueError, match="expected 4 rows"):
        parse_csv(_build_csv(rows))


def test_rejects_unknown_axis():
    header = ["axis"] + [f"s{i}" for i in range(1024)]
    rows = [header, ["X"] + [0.0] * 1024, ["Y"] + [0.0] * 1024, ["Q"] + [0.0] * 1024]
    with pytest.raises(ValueError, match="unknown axis"):
        parse_csv(_build_csv(rows))


def test_rejects_duplicate_axis():
    header = ["axis"] + [f"s{i}" for i in range(1024)]
    rows = [header, ["X"] + [0.0] * 1024, ["X"] + [0.0] * 1024, ["Y"] + [0.0] * 1024]
    with pytest.raises(ValueError, match="duplicate row"):
        parse_csv(_build_csv(rows))


def test_rejects_nan():
    header = ["axis"] + [f"s{i}" for i in range(1024)]
    bad = [0.0] * 1024
    bad[42] = float("nan")
    rows = [header, ["X"] + bad, ["Y"] + [0.0] * 1024, ["Z"] + [0.0] * 1024]
    with pytest.raises(ValueError, match="NaN or inf"):
        parse_csv(_build_csv(rows))


def test_tolerates_bom():
    header = ["axis"] + [f"s{i}" for i in range(1024)]
    rows = [header] + [[ax] + [0.0] * 1024 for ax in ("X", "Y", "Z")]
    raw = ("﻿" + _build_csv(rows)).encode("utf-8")
    tensor = parse_csv(raw)
    assert tensor.shape == (3, 1024)
