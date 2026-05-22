const SEVERITY_LABEL = {
  baseline: "HEALTHY",
  low: "LOW",
  medium: "MEDIUM",
  high: "HIGH",
};

const INGESTOR_LABELS = {
  SyntheticIngestor: "DEMO · SYNTHETIC",
  JsonlReplayIngestor: "REPLAY · JSONL",
  SerialIngestor: "SENSOR · SERIAL",
};

let currentIngestor = null;

function ingestorLabel(rawName) {
  if (!rawName) return null;
  return INGESTOR_LABELS[rawName] || rawName;
}

function resolveAssetText(device_id) {
  return device_id || ingestorLabel(currentIngestor) || null;
}

const SEVERITY_BORDER_CLASS = {
  baseline: "healthy",
  low: "low",
  medium: "medium",
  high: "high",
};

const AMBIENT_CLASSES = [
  "severity-baseline",
  "severity-low",
  "severity-medium",
  "severity-high",
];

function setAmbient(severity) {
  document.body.classList.remove(...AMBIENT_CLASSES);
  const sev = (severity || "").toLowerCase();
  if (SEVERITY_BORDER_CLASS[sev]) {
    document.body.classList.add(`severity-${sev}`);
  }
}

export function renderHero({
  state,
  severity,
  state_confidence,
  severity_confidence,
  device_id,
  timestamp,
}) {
  const heroEl = document.getElementById("hero");
  const stateEl = document.getElementById("hero-state");
  const badgeEl = document.getElementById("hero-badge");
  const assetEl = document.getElementById("hero-asset");
  const timeEl = document.getElementById("hero-time");
  const confEl = document.getElementById("hero-conf");
  const sevConfEl = document.getElementById("hero-sev-conf");

  stateEl.textContent = (state || "—").toUpperCase();

  const assetText = resolveAssetText(device_id);
  const wrapEl = document.getElementById("hero-source-wrap");
  if (assetText) {
    wrapEl.hidden = false;
    assetEl.textContent = assetText;
  } else {
    wrapEl.hidden = true;
  }

  const sev = (severity || "").toLowerCase();
  badgeEl.className = "badge";
  badgeEl.textContent = SEVERITY_LABEL[sev] || (severity || "—").toUpperCase();

  heroEl.classList.remove("healthy", "low", "medium", "high", "stale");
  if (SEVERITY_BORDER_CLASS[sev]) heroEl.classList.add(SEVERITY_BORDER_CLASS[sev]);

  setAmbient(sev);

  confEl.textContent = formatPct(state_confidence);
  sevConfEl.textContent = formatPct(severity_confidence);

  if (timestamp) {
    const d = new Date(timestamp * 1000);
    timeEl.textContent = d.toLocaleTimeString();
  }
}

function formatPct(v) {
  if (v == null || Number.isNaN(v)) return "—";
  return (v * 100).toFixed(1) + "%";
}

export function setAssetCard({ device_id, online }) {
  document.getElementById("asset-id").textContent = resolveAssetText(device_id) || "—";
  const dot = document.getElementById("asset-dot");
  dot.classList.toggle("connected", !!online);
  dot.classList.toggle("danger", !online);
  document.getElementById("asset-status-text").textContent = online ? "Active" : "Offline";
}

export function setMetaPanel({ model_id, ingestor }) {
  if (model_id) document.getElementById("meta-model").textContent = model_id;
  if (ingestor) {
    document.getElementById("meta-ingestor").textContent = ingestor;
    currentIngestor = ingestor;
    // Eagerly populate the asset card so it doesn't sit at "—" before the first prediction.
    const idEl = document.getElementById("asset-id");
    if (!idEl.textContent || idEl.textContent === "—") {
      idEl.textContent = ingestorLabel(ingestor) || "—";
    }
  }
}

export function resetHero() {
  const heroEl = document.getElementById("hero");
  heroEl.classList.remove("healthy", "low", "medium", "high", "stale");

  setAmbient(null);

  document.getElementById("hero-state").textContent = "AWAITING DATA";

  const badgeEl = document.getElementById("hero-badge");
  badgeEl.className = "badge";
  badgeEl.textContent = "—";

  document.getElementById("hero-asset").textContent = "—";
  const wrapEl = document.getElementById("hero-source-wrap");
  if (wrapEl) wrapEl.hidden = true;
  document.getElementById("hero-time").textContent = "";
  document.getElementById("hero-conf").textContent = "—";
  document.getElementById("hero-sev-conf").textContent = "—";
}

export function setHeroStale(secsSince, kind = "stale") {
  const heroEl = document.getElementById("hero");
  heroEl.classList.remove("healthy", "low", "medium", "high");
  heroEl.classList.add("stale");

  setAmbient(null);

  const stateEl = document.getElementById("hero-state");
  stateEl.textContent = kind === "disconnected" ? "SENSOR DISCONNECTED" : "SENSOR SIGNAL LOST";

  const badgeEl = document.getElementById("hero-badge");
  badgeEl.className = "badge badge-warn";
  if (kind === "disconnected") {
    badgeEl.textContent = "OFFLINE";
  } else {
    badgeEl.textContent =
      secsSince != null && secsSince > 0 ? `STALE · ${secsSince}s AGO` : "STALE";
  }

  document.getElementById("hero-conf").textContent = "—";
  document.getElementById("hero-sev-conf").textContent = "—";
}
