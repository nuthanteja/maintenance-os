import numpy as np

from .events import AxisEvent, Triplet

_AXES = ("X", "Y", "Z")


class TripletBuffer:
    """Latest-window-per-axis buffer. Emits a Triplet once each of X, Y, Z has
    received a fresh sample since the last emit, and the per-axis timestamps
    are within `max_age_s` of each other.

    On emit, the freshness flags reset — three new arrivals are required for
    the next prediction. This caps the prediction rate at sensor_rate / 3,
    avoiding stale-axis predictions.
    """

    def __init__(self, max_age_s: float = 1.0) -> None:
        self._latest: dict[str, AxisEvent] = {}
        self._fresh: set[str] = set()
        self._max_age_s = max_age_s

    def push(self, event: AxisEvent) -> Triplet | None:
        if event.axis not in _AXES:
            return None
        if event.samples.shape != (1024,):
            raise ValueError(
                f"axis {event.axis} samples have shape {event.samples.shape}, expected (1024,)"
            )

        self._latest[event.axis] = event
        self._fresh.add(event.axis)

        if not set(_AXES).issubset(self._fresh):
            return None

        timestamps = [self._latest[a].timestamp for a in _AXES]
        if max(timestamps) - min(timestamps) > self._max_age_s:
            return None

        tensor = np.stack([self._latest[a].samples for a in _AXES], axis=0)
        device_id = self._latest["X"].device_id
        triplet_ts = max(timestamps)
        self._fresh.clear()
        return Triplet(timestamp=triplet_ts, tensor=tensor, device_id=device_id)
