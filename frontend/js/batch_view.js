import { postBatchPredict } from "./api.js";
import { renderHero } from "./hero.js";
import {
  createTimePlot,
  createSpectrumPlot,
  setTimeSeries,
  setSpectrum,
  renderStatsTable,
} from "./plots.js";

let timeChart = null;
let fftChart = null;
let envChart = null;

export function initBatchView() {
  const zone = document.getElementById("upload-zone");
  const input = document.getElementById("upload-input");
  const submit = document.getElementById("upload-submit");
  const rpmInput = document.getElementById("upload-rpm");
  const errorEl = document.getElementById("upload-error");
  const results = document.getElementById("batch-results");

  let pickedFile = null;

  function setError(msg) {
    if (msg) {
      errorEl.textContent = msg;
      errorEl.hidden = false;
    } else {
      errorEl.hidden = true;
    }
  }

  function pickFile(file) {
    pickedFile = file;
    if (file) {
      submit.textContent = `Analyze (${file.name})`;
      submit.disabled = false;
      setError(null);
    }
  }

  zone.addEventListener("click", (e) => {
    if (e.target.closest("button") || e.target.closest("input")) return;
    input.click();
  });

  input.addEventListener("change", () => {
    if (input.files.length) pickFile(input.files[0]);
  });

  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("dragging");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragging"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragging");
    if (e.dataTransfer.files.length) pickFile(e.dataTransfer.files[0]);
  });

  submit.disabled = true;
  submit.addEventListener("click", async () => {
    if (!pickedFile) {
      setError("Pick a file first");
      return;
    }
    const rpm = Number(rpmInput.value);
    if (!Number.isFinite(rpm) || rpm <= 0) {
      setError("RPM must be a positive number");
      return;
    }
    submit.disabled = true;
    submit.textContent = "Analyzing…";
    try {
      const res = await postBatchPredict(pickedFile, rpm);
      renderHero({ ...res.prediction, device_id: pickedFile.name, timestamp: Date.now() / 1000 });
      ensureCharts();
      setTimeSeries(timeChart, res.plot_data.time_domain);
      setSpectrum(fftChart, res.plot_data.frequency_domain);
      setSpectrum(envChart, res.plot_data.envelope_spectrum);
      renderStatsTable(document.getElementById("batch-stats"), res.plot_data.stats);
      results.hidden = false;
    } catch (e) {
      setError(`Prediction failed: ${e.message}`);
    } finally {
      submit.disabled = false;
      submit.textContent = pickedFile ? `Analyze (${pickedFile.name})` : "Analyze";
    }
  });
}

function ensureCharts() {
  if (!timeChart) timeChart = createTimePlot(document.getElementById("batch-time-chart"));
  if (!fftChart) fftChart = createSpectrumPlot(document.getElementById("batch-fft-chart"));
  if (!envChart) envChart = createSpectrumPlot(document.getElementById("batch-env-chart"));
}
