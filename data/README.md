# Data layout

This directory is for raw and processed datasets. Contents are gitignored except this README.

## Source data — JSONL produced by the sensor capture script

The sensor capture script (see `MMS_Scripts/get_data_wave_uart.py`) writes one JSON object per axis-window:

```json
{"time": 1714568123.456, "axis": "X", "data": [s0, s1, ..., s1023]}
```

- `time` — Unix epoch seconds at the moment the window finished arriving on the host.
- `axis` — one of `X`, `Y`, `Z`.
- `data` — 1024 floats. **DC-removed** at capture time (`raw - mean(raw)`).

The device cycles axes (X → Y → Z → X → ...), so a single multivariate sample is built from three consecutive lines (one per axis).

## Filename convention (training data only)

JSONL files captured for labelled training are renamed by hand to encode the ground-truth labels:

```
<FaultName>_<Position>_<Duration>_<RPM>rpm_<Severity>_<Extra>.jsonl
```

Example: `MechanicalLooseness_Shaftend_10mins_2200rpm_high_360deg.jsonl`.

- `FaultName` — `Bearing_fault` | `Mechanical_Looseness` | `Misalignment` | `Unbalance` | `Normal`
- `RPM` — integer RPM with the `rpm` suffix (e.g. `2200rpm`, `2700rpm`, `3200rpm`)
- `Severity` — `baseline` | `low` | `medium` | `high` (forced to `baseline` for `Normal`)

Live capture files keep the auto-generated `<device_id>_<timestamp>.jsonl` name and are not relabelled.

## Sample rate

50 kHz, fixed by the firmware. Each window of 1024 samples therefore spans 20.48 ms.
