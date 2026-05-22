"""Parse a sensor-native JSONL file into a (3, 1024) tensor.

Each line is `{"time": <float>, "axis": "X"|"Y"|"Z", "data": [<1024 floats>]}`.
A JSONL file may contain many windows; for batch prediction we use the latest
window per axis (max `time`) and assemble them into a single triplet.
"""
import json

import numpy as np
from numpy.typing import NDArray

from .preprocess import dc_remove

EXPECTED_SAMPLES = 1024
EXPECTED_AXES = ("X", "Y", "Z")


def parse_jsonl(content: bytes | str) -> NDArray:
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")

    latest: dict[str, tuple[float, list]] = {}

    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"line {line_no}: invalid JSON ({e.msg})") from e

        axis = str(obj.get("axis", "")).strip().upper()
        if axis not in EXPECTED_AXES:
            continue  # tolerate stray axes

        data = obj.get("data")
        if not isinstance(data, list) or len(data) != EXPECTED_SAMPLES:
            raise ValueError(
                f"line {line_no}: axis {axis} has {len(data) if isinstance(data, list) else 'no'} "
                f"samples, expected {EXPECTED_SAMPLES}"
            )

        timestamp = float(obj.get("time", 0.0))
        if axis not in latest or timestamp > latest[axis][0]:
            latest[axis] = (timestamp, data)

    missing = set(EXPECTED_AXES) - latest.keys()
    if missing:
        raise ValueError(f"missing axes in JSONL: {sorted(missing)}")

    tensor = np.stack(
        [np.asarray(latest[a][1], dtype=np.float64) for a in EXPECTED_AXES],
        axis=0,
    )
    if not np.all(np.isfinite(tensor)):
        raise ValueError("JSONL contains NaN or inf samples")

    return dc_remove(tensor)
