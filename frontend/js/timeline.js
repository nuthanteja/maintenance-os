const _STYLE_CACHE = {};

function severityColor(severity) {
  if (!_STYLE_CACHE.cs) _STYLE_CACHE.cs = getComputedStyle(document.documentElement);
  const cs = _STYLE_CACHE.cs;
  const map = {
    baseline: cs.getPropertyValue("--healthy").trim(),
    low: cs.getPropertyValue("--low").trim(),
    medium: cs.getPropertyValue("--medium").trim(),
    high: cs.getPropertyValue("--high").trim(),
  };
  return map[severity] || null;
}

export class SeverityTimeline {
  constructor(canvasEl, capacity = 60) {
    this.canvas = canvasEl;
    this.ctx = canvasEl.getContext("2d");
    this.cap = capacity;
    this.buf = new Array(capacity).fill(null);
    this.head = 0;
    this._resize();
    new ResizeObserver(() => this._resize()).observe(canvasEl);
  }

  push(severity) {
    this.buf[this.head] = (severity || "").toLowerCase();
    this.head = (this.head + 1) % this.cap;
    this._draw();
  }

  reset() {
    this.buf.fill(null);
    this.head = 0;
    this._draw();
  }

  resize() {
    this._resize();
  }

  _resize() {
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    if (w === 0 || h === 0) return;
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.round(w * dpr);
    this.canvas.height = Math.round(h * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this._draw();
  }

  _draw() {
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    if (w === 0 || h === 0) return;

    this.ctx.clearRect(0, 0, w, h);
    this.ctx.fillStyle = "rgba(255, 255, 255, 0.025)";
    this.ctx.fillRect(0, 0, w, h);

    const colW = w / this.cap;
    const drawW = Math.max(1, Math.ceil(colW));
    for (let i = 0; i < this.cap; i++) {
      const slotIdx = (this.head + i) % this.cap;
      const sev = this.buf[slotIdx];
      if (!sev) continue;
      const color = severityColor(sev);
      if (!color) continue;
      this.ctx.fillStyle = color;
      this.ctx.fillRect(i * colW, 0, drawW, h);
    }
  }
}
