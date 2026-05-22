import { StreamClient } from "./api.js";
import { renderHero, setAssetCard, setMetaPanel, setHeroStale } from "./hero.js";
import {
  createTimePlot,
  createSpectrumPlot,
  setTimeSeries,
  setSpectrum,
  renderStatsTable,
} from "./plots.js";
import { SeverityTimeline } from "./timeline.js";
import { pushHistory } from "./history.js";

let client = null;
let timeChart = null;
let fftChart = null;
let envChart = null;
let timeline = null;

const RATE_WINDOW_MS = 3000;
const STALE_THRESHOLD_MS = 5000;
const STALE_CHECK_INTERVAL_MS = 1000;
let predTimes = [];
let currentMode = "batch";
let lastPredictionAt = null;
let wsConnected = false;
let connState = "connecting"; // "connected" | "stale" | "disconnected" | "connecting"

export function initStreamView() {
  const ecoToggle = document.getElementById("eco-toggle");
  const rpmInput = document.getElementById("stream-rpm");
  const ecoMsg = document.getElementById("eco-msg");
  const plots = document.getElementById("stream-plots");
  const rateEl = document.getElementById("stream-rate");

  timeline = new SeverityTimeline(document.getElementById("severity-canvas"));

  document.addEventListener("mode-change", (e) => {
    currentMode = e.detail.mode;
    if (currentMode === "stream") {
      // Canvas was display:none and may have lost dimensions; force a resize+repaint
      requestAnimationFrame(() => timeline.resize());
    }
  });

  client = new StreamClient();
  client.on("open", () => {
    wsConnected = true;
    applyConnState();
  });
  client.on("close", () => {
    wsConnected = false;
    applyConnState();
  });
  client.on("error", () => {
    wsConnected = false;
    applyConnState();
  });

  setInterval(applyConnState, STALE_CHECK_INTERVAL_MS);

  client.on("status", (msg) => {
    if (msg.ingestor) setMetaPanel({ ingestor: msg.ingestor });
    if (msg.rpm != null) rpmInput.value = msg.rpm;
  });

  client.on("prediction", (msg) => {
    const f = msg.frame;
    lastPredictionAt = Date.now();
    if (connState !== "connected") {
      connState = "connected";
      applyConnState();
    }
    setAssetCard({ device_id: f.device_id, online: true });
    if (timeline) timeline.push(f.severity);
    pushHistory({ state: f.state, severity: f.severity, timestamp: f.timestamp });
    predTimes.push(performance.now());
    const cutoff = performance.now() - RATE_WINDOW_MS;
    predTimes = predTimes.filter((t) => t >= cutoff);
    if (currentMode !== "stream") return;
    renderHero(f);
    rateEl.textContent = ((predTimes.length / RATE_WINDOW_MS) * 1000).toFixed(1) + " pred/s";
  });

  client.on("plot", (msg) => {
    if (currentMode !== "stream") return;
    if (ecoToggle.checked) return;
    ensureCharts();
    setTimeSeries(timeChart, msg.data.time_domain);
    setSpectrum(fftChart, msg.data.frequency_domain);
    setSpectrum(envChart, msg.data.envelope_spectrum);
    renderStatsTable(document.getElementById("stream-stats"), msg.data.stats);
  });

  ecoToggle.addEventListener("change", () => {
    client.setEco(ecoToggle.checked);
    plots.hidden = ecoToggle.checked;
    ecoMsg.hidden = !ecoToggle.checked;
  });

  rpmInput.addEventListener("change", () => {
    const v = Number(rpmInput.value);
    if (Number.isFinite(v) && v > 0) client.setRpm(v);
  });

  client.connect();
}

function ensureCharts() {
  if (!timeChart) timeChart = createTimePlot(document.getElementById("stream-time-chart"));
  if (!fftChart) fftChart = createSpectrumPlot(document.getElementById("stream-fft-chart"));
  if (!envChart) envChart = createSpectrumPlot(document.getElementById("stream-env-chart"));
}

function applyConnState() {
  const now = Date.now();
  let state;
  let secsStale = 0;

  if (!wsConnected) {
    state = "disconnected";
  } else if (lastPredictionAt && now - lastPredictionAt > STALE_THRESHOLD_MS) {
    state = "stale";
    secsStale = Math.floor((now - lastPredictionAt) / 1000);
  } else {
    state = "connected";
  }

  const transitioning = state !== connState;
  connState = state;

  const dot = document.getElementById("conn-dot");
  const txt = document.getElementById("conn-text");
  dot.classList.remove("connected", "warning", "danger");

  if (state === "connected") {
    dot.classList.add("connected");
    txt.textContent = "SYSTEM CONNECTED";
  } else if (state === "stale") {
    dot.classList.add("warning");
    txt.textContent = `SENSOR STALE · ${secsStale}s`;
    if (currentMode === "stream") setHeroStale(secsStale, "stale");
  } else if (state === "disconnected") {
    dot.classList.add("danger");
    txt.textContent = "DISCONNECTED";
    if (currentMode === "stream" && transitioning) {
      const secs = lastPredictionAt ? Math.floor((now - lastPredictionAt) / 1000) : 0;
      setHeroStale(secs, "disconnected");
    }
  }
}
