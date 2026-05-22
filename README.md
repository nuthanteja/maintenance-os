# Maintenance_OS

**Live UI preview:** <https://nuthanteja.github.io/maintenance-os/> — static demo of the dashboard with synthetic predictions cycling through every severity (no backend required to view). For real inference, clone and run the FastAPI server locally.

**Project report:** [`docs/Project_report_Team_Delta.pdf`](docs/Project_report_Team_Delta.pdf) — full writeup covering system design, modelling experiments, results, and the path from notebook to deployed product.

**Research notebooks:** [`docs/notebooks/`](docs/notebooks/) — Colab notebooks for data analysis, feature engineering, and modelling experiments (1D-CNN variants across sensor configurations, severity-based classification, plot-selection analysis). Each notebook has a header cell describing its purpose.

---

Vibration-based predictive maintenance system for rotary machinery — backend service plus operator dashboard. Loads a trained model bundle, ingests tri-axial accelerometer data (X/Y/Z @ 50 kHz, 1024-sample windows), and classifies machine state and severity in real time. Severity outputs map to **ISO 20816-3 Action Zones** (A/B/C/D).

The current shipped model is **MiniRocket + dual RidgeClassifierCV** (sktime + scikit-learn). The model layer sits behind a `Predictor` ABC so swapping in a new architecture (CNN, Transformer, etc.) requires no API changes.

---

## Three operating modes

| Mode | What it does | Where it lives |
|---|---|---|
| **CSV Batch Analysis** | Upload a single time-window (CSV or JSONL) → returns prediction + plot data (time, FFT, envelope spectrum, stats). | `POST /api/batch/predict` |
| **Real-time Sensor Monitoring** | WebSocket stream of predictions (and optional plot frames) from a live or simulated source. Per-client eco mode suppresses heavy plot frames. | `WS /ws/stream` |
| **Recent Predictions** | Operator-facing log of recent predictions with state, severity, and dedup counts. Backed by client-side history; data continues collecting in the background. | Frontend page |

---

## Quickstart

```powershell
# 1. create + activate a venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. install (editable, with dev deps)
pip install -e ".[dev]"

# 3. run the test suite
#    Unit tests for predictor, pipeline, buffer, ISO mapping
#    Integration tests for batch endpoint + WS stream endpoint
pytest -v

# 4. start the server (FastAPI + uvicorn, serves API and frontend on one port)
uvicorn pmos.api.app:app --reload
```

Open **<http://127.0.0.1:8000>** for the dashboard. **<http://127.0.0.1:8000/docs>** for the auto-generated OpenAPI UI.

By default the backend uses the `synthetic` ingestor, so the stream pipeline works without any sensor hardware or replay file.

---

## Running modes (data sources)

The backend has three swappable real-time ingestors. Pick one via `PMOS_INGESTOR`:

### 1. Synthetic — default, no setup

Generates sine + harmonics + noise per axis. Predictions on this data are *not meaningful* (the model wasn't trained on synthetic signals) — purpose is to verify the full pipeline end-to-end without hardware.

```powershell
# (this is the default; nothing to set)
uvicorn pmos.api.app:app --reload
```

### 2. Replay — play back a recorded JSONL file

Replays a saved sensor capture at original timing (or as-fast-as-possible). Useful for demos with realistic data, regression checks, and validating the model on known-labelled files.

```powershell
$env:PMOS_INGESTOR     = "replay"
$env:PMOS_REPLAY_PATH  = "path/to/Bearing_fault_..._high_360deg.jsonl"
$env:PMOS_REPLAY_REALTIME = "true"   # original timing; set "false" for as-fast-as-possible
$env:PMOS_REPLAY_LOOP  = "true"      # loop forever once the file ends
uvicorn pmos.api.app:app --reload
```

### 3. Serial — live sensor over UART

Reads from `pyserial` and parses the ASCII-hex frame format used by `MMS_Scripts/get_data_wave_uart.py`. Each line is `<device_id> <axis> <hex_s0> ... <hex_s1023>\n`. DC removal is applied host-side before the window is buffered, matching the capture script's behavior.

```powershell
# Find your COM port first:
#   Windows : Device Manager → Ports (COM & LPT)        — typically COM3 / COM4
#   Linux   : ls /dev/ttyUSB* /dev/ttyACM*              — typically /dev/ttyUSB0
#   macOS   : ls /dev/tty.usb*                          — typically /dev/tty.usbserial-XXXX

# Make sure no other process has the port open (close get_data_wave_uart.py
# or any serial monitor first — only one process can hold a port).

$env:PMOS_INGESTOR        = "serial"
$env:PMOS_SERIAL_PORT     = "COM3"        # whatever yours is
$env:PMOS_SERIAL_BAUDRATE = "921600"      # matches the firmware
$env:PMOS_DEFAULT_RPM     = "2700"        # the speed the machine is currently running at

uvicorn pmos.api.app:app --reload
```

Then open <http://127.0.0.1:8000>, switch to **Real-time Sensors** — within a second or two of the firmware sending the first X/Y/Z cycle, predictions start streaming.

**Operational notes:**
- The asset card and hero source line populate from the `device_id` the firmware emits in each line.
- RPM can be changed live from any connected client without restarting the server: send `{"type": "set_rpm", "rpm": 2700}` over the WS, or just change the value in the RPM input on the dashboard's stream view.
- If the firmware stops emitting (e.g. sensor unplugged), the dashboard's stale-data detection fires after 5 s — hero fades to neutral, topbar drops to amber `SENSOR STALE · Xs`. WS disconnect goes red `DISCONNECTED`.
- On Linux the user running the server needs to be in the `dialout` group (`sudo usermod -a -G dialout $USER`, then re-login) to read from a serial device.

---

## Layout

```
src/pmos/                  backend package (`pmos`)
  config.py                pydantic-settings (env + .env, PMOS_* vars)
  core/
    enums.py               Severity, IsoZone
    schemas.py             Prediction, PredictionFrame, PlotData, BatchPredictionResponse
  models/
    base.py                Predictor ABC
    minirocket.py          MiniRocketPredictor (joblib bundle wrapper)
    registry.py            id → Predictor factory
  inference/
    iso.py                 severity → ISO 20816-3 zone mapping
    service.py             PredictionService facade
  pipeline/
    csv_loader.py          batch CSV → (3, 1024) tensor
    jsonl_loader.py        sensor-native JSONL → latest triplet → (3, 1024)
    preprocess.py          idempotent DC removal
    plots.py               time-domain, FFT, envelope spectrum, stats
  streaming/
    events.py              AxisEvent, Triplet dataclasses
    buffer.py              TripletBuffer (latest-window-per-axis with freshness reset)
    ingestor.py            BaseIngestor ABC
    synthetic.py           sine + harmonics + noise (default — clone-and-run demo)
    replay.py              JSONL replay at original or as-fast-as-possible timing
    serial_ingestor.py     real pyserial reader, mirrors get_data_wave_uart.py
    manager.py             StreamManager (singleton, owns ingestor + buffer + clients)
  api/
    app.py                 FastAPI factory + lifespan
    deps.py                injected predictor + ingestor builder
    routes/
      health.py            GET /health
      meta.py              GET /api/meta
      batch.py             POST /api/batch/predict
      stream.py            WS /ws/stream

frontend/                  static SPA (vanilla HTML + Tailwind-style CSS + uPlot)
  index.html               single page, three views (Batch / Real-time / Recent Predictions)
  css/styles.css           dark industrial design system, severity color theming
  js/
    main.js                entrypoint, mode router
    api.js                 REST + WS client
    hero.js                hero card (state, severity badge, confidences)
    plots.js               uPlot wrappers (time, FFT, envelope), stats table
    timeline.js            severity timeline strip (last 60 predictions)
    history.js             recent predictions feed (dedup + count)
    batch_view.js          drag-drop upload, batch results render
    stream_view.js         WS lifecycle, eco toggle, stale-data detection

models/                    serialized model bundles
  minirocket_pipeline.joblib
  model_card.yaml          input contract, classes, ISO mapping reference

docs/                      project documentation
  Project_report_Team_Delta.pdf    full project report (system design, experiments, results)
  notebooks/                       Colab notebooks (modelling experiments + data analysis)

tests/
  unit/                    predictor, pipeline, buffer, ISO mapping, ingestors
  integration/             batch endpoint, WS endpoint
  conftest.py              shared fixtures (joblib path, RNG, synthetic window)

scripts/
  run_dev.ps1              dev server runner
  replay_stream.py         standalone WS client (prints prediction frames)
```

---

## Configuration

All settings are env-driven via `PMOS_*` variables. Copy `.env.example` → `.env` and edit, or export in the shell.

| Variable | Default | Purpose |
|---|---|---|
| `PMOS_LOG_LEVEL` | `INFO` | Python logging level |
| `PMOS_API_HOST` | `127.0.0.1` | uvicorn bind host |
| `PMOS_API_PORT` | `8000` | uvicorn bind port |
| `PMOS_CORS_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | comma-separated CORS allowlist |
| `PMOS_PREDICTOR_ID` | `minirocket` | which Predictor class to load (registered in `models/registry.py`) |
| `PMOS_PREDICTOR_PATH` | `models/minirocket_pipeline.joblib` | path to the model bundle |
| `PMOS_INGESTOR` | `synthetic` | one of `synthetic` / `replay` / `serial` |
| `PMOS_REPLAY_PATH` | `data/samples/replay.jsonl` | JSONL file for the replay ingestor |
| `PMOS_REPLAY_REALTIME` | `true` | replay at original timing, vs as-fast-as-possible |
| `PMOS_REPLAY_LOOP` | `true` | loop the replay file forever |
| `PMOS_SERIAL_PORT` | `COM3` | pyserial port for the serial ingestor |
| `PMOS_SERIAL_BAUDRATE` | `921600` | matches `get_data_wave_uart.py` |
| `PMOS_DEFAULT_RPM` | `2700` | server-wide RPM used for predictions in stream mode (clients can change via WS) |
| `PMOS_TRIPLET_MAX_AGE_S` | `1.0` | max time skew tolerance between X/Y/Z windows in the TripletBuffer |

---

## API surface

### REST

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | liveness probe |
| `GET` | `/api/meta` | model id, state/severity classes, ISO zones, input contract |
| `POST` | `/api/batch/predict` | `multipart/form-data` with `file=` (CSV or JSONL) and `rpm=` form field. Returns prediction + plot data. |

### WebSocket — `/ws/stream`

**Server → client messages:**

```json
{"type": "status", "ingestor": "JsonlReplayIngestor", "rpm": 2700, "eco_mode": false}
{"type": "prediction", "frame": {<PredictionFrame>}}      // every full triplet
{"type": "plot", "timestamp": <epoch>, "data": {<PlotData>}}   // every triplet, suppressed when eco_mode=true
{"type": "pong"}
{"type": "error", "message": "..."}
```

**Client → server messages:**

```json
{"type": "set_eco", "eco": true}      // per-client toggle
{"type": "set_rpm", "rpm": 2700}      // server-wide (one machine = one RPM)
{"type": "ping"}
```

---

## Data contracts

### Sensor protocol (real hardware)

Mirrored from `MMS_Scripts/get_data_wave_uart.py`. ASCII line over UART:

```
<device_id> <axis> <hex_s0> <hex_s1> ... <hex_s1023>\n
```

- 50 kHz sampling, 1024 samples per axis-window (= 20.48 ms per window)
- Samples are 32-bit unsigned ints in hex; DC removal applied host-side
- Device cycles X → Y → Z, one line per axis-window
- Files are `.jsonl` with rows `{"time": <float>, "axis": "X"|"Y"|"Z", "data": [<1024 floats>]}`

### Batch upload formats

**CSV** (recommended for one-off uploads):
```
axis,s0,s1,s2,...,s1023
X,1.2,3.4,...
Y,...
Z,...
```
RPM is sent as a separate form field; not embedded in the CSV.

**JSONL** (sensor-native, also accepted): same format the capture script writes. Backend uses the latest valid X/Y/Z triplet.

### Model input contract

`(N, 3, 1024)` float tensor in axis order X, Y, Z. Plus a scalar `rpm` (revolutions per minute). Output: machine state class + severity class + per-head confidence + ISO 20816-3 zone code.

Confidences are derived from `RidgeClassifierCV.decision_function` margins via softmax (multiclass) or sigmoid (binary). Documented in `models/model_card.yaml` as **relative ranking, not calibrated probability**.

---

## Frontend

Single-page app served from `/` by FastAPI's `StaticFiles`. No build step required for development — `index.html` references uPlot from CDN and uses ES modules directly.

### Design system

- **Theme:** dark industrial control-room aesthetic
- **Severity colors:** `--healthy` green / `--low` yellow / `--medium` orange / `--high` red
- **Glanceable awareness:** the entire viewport gets a colored border + inner glow keyed to the current severity, so an operator picks up machine state from peripheral vision without focusing on any value (clinical-monitor pattern)
- **Hero card:** background tints with the same severity color; state name + neutral severity badge + fault confidence (large mono) + severity confidence (small footnote)
- **Severity timeline:** 60-column rhythm strip below the hero on stream view — solid color band = consistent prediction, speckled = model flickering between severities
- **Stale detection:** if no prediction frame arrives for >5 s, hero fades to neutral, topbar drops to amber `SENSOR STALE · Xs`. WS disconnect goes red `DISCONNECTED`. Fail loud, never silent.
- **Recent Predictions:** dedicated page with full list — time / state / severity / `×count` per row. Consecutive identical predictions dedup to one row; the count tells you how many sample windows agreed.

### Plot panels (Real-time + Batch)

| Panel | Source |
|---|---|
| Time-Domain Waveform | raw 3-axis samples |
| FFT Magnitude Spectrum | `np.fft.rfft` per axis |
| Envelope Spectrum (Bearing Diagnostic) | Hilbert-envelope FFT — picks up bearing characteristic frequencies |
| Diagnostic Statistics | per-axis RMS, peak, crest factor, kurtosis |

Y-axis uses asymmetric EMA smoothing (fast growth, slow decay) so spikes don't lock the scale and steady signals don't jitter.

---

## Swap points

The two big extension points are ABCs — implement and register:

### Replacing the model

1. Add a class implementing `pmos.models.base.Predictor` (in a new file under `pmos/models/`).
2. Register it in `pmos/models/registry.py`:
   ```python
   _REGISTRY["my_new_model"] = MyNewPredictor
   ```
3. Set `PMOS_PREDICTOR_ID=my_new_model` and `PMOS_PREDICTOR_PATH=...`.

The `Prediction` schema, `/api/meta`, batch and stream endpoints all keep working. The model-card YAML and README should be updated, but no API consumer changes.

### Adding a new ingestor

1. Subclass `pmos.streaming.ingestor.BaseIngestor` and implement the `events()` async iterator.
2. Add a branch to `pmos.api.deps.build_ingestor`.
3. Set `PMOS_INGESTOR=...`.

---

## Testing

```powershell
pytest -v                       # full suite (~50 tests)
pytest tests/unit -v            # unit only (fast, no joblib needed for some)
pytest tests/integration -v     # API roundtrips (TestClient + WS)
```

Unit tests cover:
- `MiniRocketPredictor` end-to-end on a synthetic window
- CSV / JSONL loaders (valid + malformed cases)
- `TripletBuffer` (XYZ alignment, freshness reset, age tolerance)
- `SyntheticIngestor` axis cycle, `JsonlReplayIngestor` ordering and looping
- ISO 20816-3 zone mapping

Integration tests cover:
- `/health`, `/api/meta`
- `POST /api/batch/predict` with both CSV and JSONL bodies, error paths
- WS prediction frames, eco-mode plot suppression, ping/pong

---

## Deployment

Currently optimized for **laptop demo to the client** — clone, install, run uvicorn, open browser. Tailwind CDN + uPlot CDN means no build step.

For production:
- Vendor `uPlot.iife.min.js` and add a Tailwind PostCSS build (or replace Tailwind utilities with the existing custom CSS — the design system is mostly hand-rolled already)
- Add a `Dockerfile` (single-stage Python image is fine; the joblib + scipy + numba install dominates image size)
- Set `PMOS_API_HOST=0.0.0.0`, configure CORS for the deployed frontend origin
- Switch ingestor to `serial` for live sensors (or pipe MQTT/OPC-UA into a custom ingestor)

---

## Acknowledgements

Built as a Student Data Science Consultant engagement for **[Machinery Monitoring Systems, LLC](https://mmsysllc.com/)**, in collaboration with the **[Institute for Artificial Intelligence and Data Science](https://www.buffalo.edu/ai-data-science.html)**, University at Buffalo.
