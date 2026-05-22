import numpy as np
import pytest

from pmos.streaming.buffer import TripletBuffer
from pmos.streaming.events import AxisEvent


def _evt(axis: str, t: float, val: float = 0.0) -> AxisEvent:
    return AxisEvent(timestamp=t, axis=axis, samples=np.full(1024, val), device_id="dev")


def test_emits_after_xyz_seen():
    buf = TripletBuffer()
    assert buf.push(_evt("X", 1.0)) is None
    assert buf.push(_evt("Y", 1.01)) is None
    triplet = buf.push(_evt("Z", 1.02))
    assert triplet is not None
    assert triplet.tensor.shape == (3, 1024)
    assert triplet.timestamp == pytest.approx(1.02)


def test_requires_three_fresh_arrivals_after_emit():
    buf = TripletBuffer()
    buf.push(_evt("X", 1.0))
    buf.push(_evt("Y", 1.0))
    assert buf.push(_evt("Z", 1.0)) is not None  # first emit

    # A single new arrival is not enough for the next emit.
    assert buf.push(_evt("X", 2.0)) is None
    assert buf.push(_evt("Y", 2.0)) is None
    assert buf.push(_evt("Z", 2.0)) is not None


def test_skips_emit_when_axes_too_far_apart():
    buf = TripletBuffer(max_age_s=0.1)
    buf.push(_evt("X", 1.0))
    buf.push(_evt("Y", 1.05))
    assert buf.push(_evt("Z", 5.0)) is None  # Z is way newer than X


def test_unknown_axis_ignored():
    buf = TripletBuffer()
    assert buf.push(_evt("Q", 1.0)) is None


def test_rejects_wrong_sample_shape():
    buf = TripletBuffer()
    bad = AxisEvent(timestamp=1.0, axis="X", samples=np.zeros(512), device_id="dev")
    with pytest.raises(ValueError, match="shape"):
        buf.push(bad)


def test_tensor_axis_order_is_xyz():
    buf = TripletBuffer()
    buf.push(_evt("Z", 1.0, val=3.0))
    buf.push(_evt("X", 1.01, val=1.0))
    buf.push(_evt("Y", 1.02, val=2.0))
    triplet = buf.push(_evt("Z", 1.03, val=3.0))
    # First emit happens on the third unique-axis arrival (the "Y" push above)
    # — re-run with a clean buffer to assert ordering deterministically.
    buf2 = TripletBuffer()
    buf2.push(_evt("Z", 1.0, val=3.0))
    buf2.push(_evt("X", 1.01, val=1.0))
    triplet = buf2.push(_evt("Y", 1.02, val=2.0))
    assert triplet is not None
    assert np.all(triplet.tensor[0] == 1.0)
    assert np.all(triplet.tensor[1] == 2.0)
    assert np.all(triplet.tensor[2] == 3.0)
