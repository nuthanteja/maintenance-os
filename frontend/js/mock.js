/**
 * Preview-mode shims: when the dashboard is served from GitHub Pages (or any
 * environment where the FastAPI backend isn't reachable), swap real network
 * I/O for synthetic data so the UI animates and shows off the design.
 *
 * Activated when:
 *   - hostname ends in `.github.io` or `.github.dev`, OR
 *   - URL has `?preview=1` (handy for local testing)
 */

export function isPreviewMode() {
  const h = location.hostname;
  return (
    h.endsWith(".github.io") ||
    h.endsWith(".github.dev") ||
    new URLSearchParams(location.search).has("preview")
  );
}

// Scripted timeline so visitors see every severity within ~40s.
// Tuple format: [state, severity, durationMs]
const SEQUENCE = [
  ["Normal", "baseline", 8000],
  ["Bearing fault", "low", 4000],
  ["Bearing fault", "medium", 5000],
  ["Bearing fault", "high", 6000],
  ["Misalignment", "medium", 5000],
  ["Unbalance", "low", 4000],
  ["Mechanical Looseness", "medium", 5000],
  ["Normal", "baseline", 5000],
];

let seqIdx = 0;
let seqStart = 0;
let plotPhase = 0;

function currentSeqEntry() {
  const now = Date.now();
  if (!seqStart) seqStart = now;
  if (now - seqStart > SEQUENCE[seqIdx][2]) {
    seqIdx = (seqIdx + 1) % SEQUENCE.length;
    seqStart = now;
  }
  return SEQUENCE[seqIdx];
}

export const MOCK_META = {
  model_id: "minirocket (preview)",
  state_classes: [
    "Bearing fault",
    "Mechanical Looseness",
    "Misalignment",
    "Normal",
    "Unbalance",
  ],
  severity_classes: ["baseline", "low", "medium", "high"],
  iso_zones: {
    A: "Zone A (Good)",
    B: "Zone B (Acceptable)",
    C: "Zone C (Warning — Unsatisfactory)",
    D: "Zone D (Alert — Unacceptable)",
  },
  input_contract: {
    tensor_shape: [3, 1024],
    axes: ["X", "Y", "Z"],
    sample_rate_hz: 50000,
    rpm_required: true,
  },
};

const SEV_TO_ZONE = { baseline: "A", low: "B", medium: "C", high: "D" };
const N = 1024;
const SAMPLE_RATE = 50000;
const AMP_BY_SEV = { baseline: 0.3, low: 0.7, medium: 1.5, high: 3.2 };

function makePrediction() {
  const [state, severity] = currentSeqEntry();
  const zone = SEV_TO_ZONE[severity];
  return {
    state,
    severity,
    state_confidence: 0.85 + Math.random() * 0.12,
    severity_confidence: 0.78 + Math.random() * 0.18,
    iso_zone: zone,
    iso_zone_label: MOCK_META.iso_zones[zone],
    rpm: 2700,
    model_id: "minirocket (preview)",
    timestamp: Date.now() / 1000,
    device_id: "PREVIEW_NODE",
  };
}

function rms(arr) {
  let s = 0;
  for (let i = 0; i < arr.length; i++) s += arr[i] * arr[i];
  return Math.sqrt(s / arr.length);
}

function peakAbs(arr) {
  let m = 0;
  for (let i = 0; i < arr.length; i++) {
    const v = arr[i] < 0 ? -arr[i] : arr[i];
    if (v > m) m = v;
  }
  return m;
}

function gauss(freq, center, width, amp) {
  const d = (freq - center) / width;
  return amp * Math.exp(-d * d);
}

function makePlot() {
  const [, severity] = currentSeqEntry();
  const amp = (AMP_BY_SEV[severity] || 1.0) * 1e5;

  const time_s = new Array(N);
  const X = new Array(N);
  const Y = new Array(N);
  const Z = new Array(N);

  for (let i = 0; i < N; i++) {
    const t = plotPhase + i / SAMPLE_RATE;
    time_s[i] = i / SAMPLE_RATE;
    X[i] =
      amp *
      (Math.sin(2 * Math.PI * 100 * t) +
        0.3 * Math.sin(2 * Math.PI * 200 * t) +
        0.1 * Math.sin(2 * Math.PI * 500 * t) +
        0.06 * (Math.random() - 0.5));
    Y[i] =
      amp *
      1.15 *
      (Math.sin(2 * Math.PI * 105 * t + 1.1) +
        0.3 * Math.sin(2 * Math.PI * 210 * t + 1.1) +
        0.06 * (Math.random() - 0.5));
    Z[i] =
      amp *
      0.9 *
      (Math.sin(2 * Math.PI * 95 * t + 2.3) +
        0.3 * Math.sin(2 * Math.PI * 190 * t + 2.3) +
        0.06 * (Math.random() - 0.5));
  }
  plotPhase += N / SAMPLE_RATE;

  // Synthetic frequency spectrum — peaks at the source frequencies.
  const nf = Math.floor(N / 2) + 1;
  const frequency_hz = new Array(nf);
  const fX = new Array(nf);
  const fY = new Array(nf);
  const fZ = new Array(nf);
  for (let i = 0; i < nf; i++) {
    const freq = (i * SAMPLE_RATE) / N;
    frequency_hz[i] = freq;
    fX[i] =
      gauss(freq, 100, 6, amp * 600) +
      gauss(freq, 200, 8, amp * 200) +
      gauss(freq, 500, 10, amp * 80);
    fY[i] =
      gauss(freq, 105, 6, amp * 700) +
      gauss(freq, 210, 8, amp * 230);
    fZ[i] =
      gauss(freq, 95, 6, amp * 540) +
      gauss(freq, 190, 8, amp * 180);
  }

  // Envelope: derived shape with lower magnitude
  const eX = fX.map((v) => v * 0.35);
  const eY = fY.map((v) => v * 0.35);
  const eZ = fZ.map((v) => v * 0.35);

  const rX = rms(X), rY = rms(Y), rZ = rms(Z);
  const pX = peakAbs(X), pY = peakAbs(Y), pZ = peakAbs(Z);

  return {
    time_domain: { time_s, X, Y, Z },
    frequency_domain: { frequency_hz, X: fX, Y: fY, Z: fZ },
    envelope_spectrum: { frequency_hz, X: eX, Y: eY, Z: eZ },
    stats: {
      rms: { X: rX, Y: rY, Z: rZ },
      peak: { X: pX, Y: pY, Z: pZ },
      crest_factor: { X: pX / rX, Y: pY / rY, Z: pZ / rZ },
      kurtosis: {
        X: 0.2 + Math.random() * 0.6,
        Y: 0.4 + Math.random() * 0.7,
        Z: 0.1 + Math.random() * 0.5,
      },
    },
  };
}

export async function mockBatchPredict(_file, rpm) {
  // Brief delay so the "Analyzing…" state is visible
  await new Promise((r) => setTimeout(r, 700));
  const pred = makePrediction();
  pred.rpm = Number(rpm) || 2700;
  return {
    prediction: pred,
    plot_data: makePlot(),
    sample_rate_hz: SAMPLE_RATE,
  };
}

export class MockStreamClient {
  constructor() {
    this._listeners = new Map();
    this._timer = null;
  }

  connect() {
    setTimeout(() => {
      this._emit("open");
      this._emit("status", {
        type: "status",
        ingestor: "PreviewIngestor",
        rpm: 2700,
        eco_mode: false,
      });
      this._startEmitting();
    }, 80);
  }

  close() {
    if (this._timer) clearInterval(this._timer);
    this._timer = null;
  }

  on(type, fn) {
    if (!this._listeners.has(type)) this._listeners.set(type, []);
    this._listeners.get(type).push(fn);
  }

  send() {}
  setEco() {}
  setRpm() {}

  _emit(type, payload) {
    const arr = this._listeners.get(type);
    if (!arr) return;
    for (const fn of arr) {
      try {
        fn(payload);
      } catch (e) {
        console.error("mock listener error", e);
      }
    }
  }

  _startEmitting() {
    this._timer = setInterval(() => {
      const frame = makePrediction();
      this._emit("prediction", { type: "prediction", frame });
      const data = makePlot();
      this._emit("plot", {
        type: "plot",
        timestamp: frame.timestamp,
        data,
      });
    }, 220);
  }
}
