const MAX_HISTORY = 200;
let entries = [];
let listEl = null;
let countLabelEl = null;
let pageVisible = false;

export function initHistory() {
  listEl = document.getElementById("history-list");
  countLabelEl = document.getElementById("history-count-label");
  const clearBtn = document.getElementById("history-clear");
  if (clearBtn) clearBtn.addEventListener("click", clearHistory);

  document.addEventListener("mode-change", (e) => {
    const wasVisible = pageVisible;
    pageVisible = e.detail.mode === "history";
    if (pageVisible && !wasVisible) render();
  });

  render();
}

export function pushHistory({ state, severity, timestamp }) {
  const ts = timestamp || Date.now() / 1000;
  const last = entries[0];
  if (last && last.state === state && last.severity === severity) {
    last.timestamp = ts;
    last.count = (last.count || 1) + 1;
  } else {
    entries.unshift({ state, severity, timestamp: ts, count: 1 });
    if (entries.length > MAX_HISTORY) entries.length = MAX_HISTORY;
  }
  if (pageVisible) render();
  if (countLabelEl) updateCountLabel();
}

function clearHistory() {
  entries = [];
  render();
}

function fmtTime(ts) {
  return new Date(ts * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function updateCountLabel() {
  if (!countLabelEl) return;
  const totalEntries = entries.length;
  const totalSamples = entries.reduce((acc, e) => acc + (e.count || 1), 0);
  countLabelEl.textContent =
    totalEntries === 0
      ? "0 entries"
      : `${totalEntries} ${totalEntries === 1 ? "entry" : "entries"} · ${totalSamples} samples`;
}

function render() {
  if (!listEl) return;
  updateCountLabel();
  listEl.replaceChildren();

  if (entries.length === 0) {
    const empty = document.createElement("div");
    empty.className = "history-empty";
    empty.textContent =
      "No predictions yet — open Real-time Sensors to start the live feed.";
    listEl.appendChild(empty);
    return;
  }

  for (const item of entries) {
    const row = document.createElement("div");
    row.className = "history-row";

    const timeEl = document.createElement("span");
    timeEl.className = "history-row-time";
    timeEl.textContent = fmtTime(item.timestamp);

    const stateEl = document.createElement("span");
    stateEl.className = "history-row-state";
    stateEl.title = item.state || "";
    stateEl.textContent = item.state || "—";

    const sevWrap = document.createElement("span");
    sevWrap.className = "history-row-severity";
    const sev = (item.severity || "").toLowerCase();

    const dotEl = document.createElement("span");
    dotEl.className = `history-dot ${sev}`;

    const sevLabel = document.createElement("span");
    sevLabel.className = `history-row-sev-label ${sev}`;
    sevLabel.textContent = (item.severity || "—").toUpperCase();

    sevWrap.appendChild(dotEl);
    sevWrap.appendChild(sevLabel);

    const countEl = document.createElement("span");
    countEl.className = "history-row-count";
    countEl.textContent = item.count > 1 ? `×${item.count}` : "";

    row.appendChild(timeEl);
    row.appendChild(stateEl);
    row.appendChild(sevWrap);
    row.appendChild(countEl);
    listEl.appendChild(row);
  }
}
