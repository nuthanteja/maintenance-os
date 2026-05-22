import { fetchMeta } from "./api.js";
import { setMetaPanel, resetHero } from "./hero.js";
import { initBatchView } from "./batch_view.js";
import { initStreamView } from "./stream_view.js";
import { initHistory } from "./history.js";
import { isPreviewMode } from "./mock.js";

const MODE_TITLES = {
  batch: "CSV Batch Analysis",
  stream: "Real-time Sensor Monitoring",
  history: "Recent Predictions",
};

async function bootstrap() {
  if (isPreviewMode()) {
    document.getElementById("preview-banner").hidden = false;
  }

  try {
    const meta = await fetchMeta();
    setMetaPanel({ model_id: meta.model_id });
  } catch (e) {
    console.warn("could not fetch /api/meta", e);
  }

  document.querySelectorAll("[data-mode]").forEach((btn) => {
    btn.addEventListener("click", () => switchMode(btn.dataset.mode));
  });

  initHistory();
  initBatchView();
  initStreamView();
  switchMode("batch");
}

function switchMode(mode) {
  document.querySelectorAll("[data-mode]").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === mode);
  });
  document.getElementById("batch-view").hidden = mode !== "batch";
  document.getElementById("stream-view").hidden = mode !== "stream";
  document.getElementById("history-view").hidden = mode !== "history";
  document.getElementById("hero").hidden = mode === "history";
  document.getElementById("mode-title").textContent = MODE_TITLES[mode] || "";

  resetHero();
  document.dispatchEvent(new CustomEvent("mode-change", { detail: { mode } }));
}

bootstrap();
