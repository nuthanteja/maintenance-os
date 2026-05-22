"""Parse the batch-upload CSV format into a (3, 1024) tensor.

Expected format:
    axis,s0,s1,...,s1023
    X,<float>,<float>,...,<float>
    Y,<float>,<float>,...,<float>
    Z,<float>,<float>,...,<float>

The first column must be the literal string `axis`. Axis order in the data rows is
not significant — they are reassembled into canonical (X, Y, Z) order by axis label.
"""
import csv
import io

import numpy as np
from numpy.typing import NDArray

from .preprocess import dc_remove

EXPECTED_SAMPLES = 1024
EXPECTED_AXES = ("X", "Y", "Z")


def parse_csv(content: bytes | str) -> NDArray:
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")  # tolerate BOM

    rows = [r for r in csv.reader(io.StringIO(content)) if r and any(c.strip() for c in r)]
    if len(rows) != 4:
        raise ValueError(
            f"expected 4 rows (1 header + 3 axes), got {len(rows)}"
        )

    header = [c.strip().lower() for c in rows[0]]
    if not header or header[0] != "axis":
        raise ValueError(
            f"first column must be 'axis', got {rows[0][0]!r}"
        )
    if len(header) != EXPECTED_SAMPLES + 1:
        raise ValueError(
            f"expected {EXPECTED_SAMPLES} sample columns, got {len(header) - 1}"
        )

    axis_to_samples: dict[str, NDArray] = {}
    for raw_row in rows[1:]:
        if len(raw_row) != EXPECTED_SAMPLES + 1:
            raise ValueError(
                f"row has {len(raw_row) - 1} samples, expected {EXPECTED_SAMPLES}"
            )
        axis = raw_row[0].strip().upper()
        if axis not in EXPECTED_AXES:
            raise ValueError(f"unknown axis {raw_row[0]!r}; expected one of X, Y, Z")
        if axis in axis_to_samples:
            raise ValueError(f"duplicate row for axis {axis}")

        try:
            samples = np.array([float(v) for v in raw_row[1:]], dtype=np.float64)
        except ValueError as e:
            raise ValueError(f"non-numeric sample in axis {axis}: {e}") from e

        if not np.all(np.isfinite(samples)):
            raise ValueError(f"axis {axis} contains NaN or inf")

        axis_to_samples[axis] = samples

    missing = set(EXPECTED_AXES) - axis_to_samples.keys()
    if missing:
        raise ValueError(f"missing axes: {sorted(missing)}")

    tensor = np.stack([axis_to_samples[a] for a in EXPECTED_AXES], axis=0)
    return dc_remove(tensor)
