const AXIS_COLORS = {
  X: getComputedStyle(document.documentElement).getPropertyValue("--x-color").trim() || "#f87171",
  Y: getComputedStyle(document.documentElement).getPropertyValue("--y-color").trim() || "#60a5fa",
  Z: getComputedStyle(document.documentElement).getPropertyValue("--z-color").trim() || "#34d399",
};

const TEXT = getComputedStyle(document.documentElement).getPropertyValue("--text-muted").trim();
const FAINT = getComputedStyle(document.documentElement).getPropertyValue("--text-faint").trim();
const GRID = getComputedStyle(document.documentElement).getPropertyValue("--border-faint").trim();

function makeStickyRange(positiveOnly) {
  // Asymmetric EMA on the y-magnitude:
  //   * grow fast (alpha_up high) so spikes don't get clipped or cause jitter
  //   * decay slower (alpha_down low) so axis doesn't twitch on normal frame-to-frame variation
  // Tuned so locked-up scales recover within ~1–2 seconds of stream throughput.
  const alpha_up = 0.5;
  const alpha_down = 0.20;
  let smoothMax = null;
  return (_self, dmin, dmax) => {
    const fallback = positiveOnly ? [0, 1] : [-1, 1];
    if (!Number.isFinite(dmin) || !Number.isFinite(dmax)) return fallback;
    const span = positiveOnly ? Math.max(dmax, 0) : Math.max(Math.abs(dmin), Math.abs(dmax));
    if (smoothMax == null || span > smoothMax * 2) {
      smoothMax = span;
    } else if (span > smoothMax) {
      smoothMax = smoothMax * (1 - alpha_up) + span * alpha_up;
    } else {
      smoothMax = smoothMax * (1 - alpha_down) + span * alpha_down;
    }
    const headroom = smoothMax * 1.1 || 1;
    return positiveOnly ? [0, headroom] : [-headroom, headroom];
  };
}

function baseOpts(xLabel, yLabel, positiveOnly) {
  return {
    width: 0,
    height: 0,
    padding: [10, 14, 10, 8],
    legend: { show: false },
    cursor: { drag: { x: false, y: false } },
    scales: {
      x: { time: false },
      y: { auto: true, range: makeStickyRange(positiveOnly) },
    },
    axes: [
      {
        stroke: TEXT,
        grid: { stroke: GRID, width: 1 },
        ticks: { stroke: GRID },
        label: xLabel,
        labelSize: 24,
        labelFont: "11px Inter",
        font: "10px Inter",
      },
      {
        stroke: TEXT,
        grid: { stroke: GRID, width: 1 },
        ticks: { stroke: GRID },
        label: yLabel,
        labelSize: 48,
        labelFont: "11px Inter",
        font: "10px Inter",
        size: 56,
      },
    ],
    series: [
      { label: xLabel },
      { label: "X", stroke: AXIS_COLORS.X, width: 1.2 },
      { label: "Y", stroke: AXIS_COLORS.Y, width: 1.2 },
      { label: "Z", stroke: AXIS_COLORS.Z, width: 1.2 },
    ],
  };
}

export function createTimePlot(container) {
  return _attach(container, baseOpts("Time (ms)", "Amplitude", false));
}

export function createSpectrumPlot(container) {
  return _attach(container, baseOpts("Frequency (Hz)", "Magnitude", true));
}

function _attach(container, opts) {
  const rect = container.getBoundingClientRect();
  opts.width = Math.max(rect.width, 200);
  opts.height = Math.max(rect.height, 200);
  const placeholder = [[0, 1], [0, 0], [0, 0], [0, 0]];
  const u = new uPlot(opts, placeholder, container);

  _wireLegend(container, u);

  new ResizeObserver(() => {
    const r = container.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) u.setSize({ width: r.width, height: r.height });
  }).observe(container);

  return u;
}

const _LEG_TO_SERIES = { "leg-x": 1, "leg-y": 2, "leg-z": 3 };

function _wireLegend(chartContainer, plot) {
  const panel = chartContainer.closest(".panel");
  if (!panel) return;
  const legend = panel.querySelector(".panel-legend");
  if (!legend) return;

  legend.querySelectorAll(".leg").forEach((el) => {
    const cls = Object.keys(_LEG_TO_SERIES).find((c) => el.classList.contains(c));
    if (!cls) return;
    const idx = _LEG_TO_SERIES[cls];
    el.addEventListener("click", () => {
      const showing = plot.series[idx].show !== false;
      plot.setSeries(idx, { show: !showing });
      el.classList.toggle("disabled", showing);
    });
  });
}

export function setTimeSeries(plot, timeSeries) {
  const xs = timeSeries.time_s.map((t) => t * 1000); // ms
  plot.setData([xs, timeSeries.X, timeSeries.Y, timeSeries.Z]);
}

export function setSpectrum(plot, spec) {
  plot.setData([spec.frequency_hz, spec.X, spec.Y, spec.Z]);
}

export function renderStatsTable(container, stats) {
  const rows = [
    ["", "X", "Y", "Z"],
    ["RMS", stats.rms.X, stats.rms.Y, stats.rms.Z],
    ["Peak", stats.peak.X, stats.peak.Y, stats.peak.Z],
    ["Crest Factor", stats.crest_factor.X, stats.crest_factor.Y, stats.crest_factor.Z],
    ["Kurtosis", stats.kurtosis.X, stats.kurtosis.Y, stats.kurtosis.Z],
  ];

  const html = rows
    .map((row, i) => {
      if (i === 0) {
        return row
          .map((c, j) => `<div class="stats-head ${j === 0 ? "" : "stats-cell"}">${c}</div>`)
          .join("");
      }
      return row
        .map((c, j) =>
          j === 0
            ? `<div class="stats-row-label">${c}</div>`
            : `<div class="stats-cell">${formatNum(c)}</div>`,
        )
        .join("");
    })
    .join("");

  container.innerHTML = html;
}

function formatNum(v) {
  if (v == null || Number.isNaN(v)) return "—";
  if (Math.abs(v) >= 1e6) return v.toExponential(2);
  if (Math.abs(v) >= 100) return v.toFixed(1);
  if (Math.abs(v) >= 1) return v.toFixed(2);
  return v.toFixed(3);
}
