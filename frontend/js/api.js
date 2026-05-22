export async function fetchMeta() {
  const r = await fetch("/api/meta");
  if (!r.ok) throw new Error(`/api/meta returned ${r.status}`);
  return r.json();
}

export async function postBatchPredict(file, rpm) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("rpm", String(rpm));
  const r = await fetch("/api/batch/predict", { method: "POST", body: fd });
  if (!r.ok) {
    let detail = `${r.status}`;
    try {
      const j = await r.json();
      detail = j.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return r.json();
}

export class StreamClient {
  constructor() {
    this._ws = null;
    this._listeners = new Map();
    this._url = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws/stream";
  }

  connect() {
    this._ws = new WebSocket(this._url);
    this._ws.addEventListener("open", () => this._emit("open"));
    this._ws.addEventListener("close", () => this._emit("close"));
    this._ws.addEventListener("error", (e) => this._emit("error", e));
    this._ws.addEventListener("message", (e) => {
      let msg;
      try {
        msg = JSON.parse(e.data);
      } catch (_) {
        return;
      }
      this._emit(msg.type, msg);
    });
  }

  close() {
    if (this._ws) this._ws.close();
  }

  on(type, fn) {
    if (!this._listeners.has(type)) this._listeners.set(type, []);
    this._listeners.get(type).push(fn);
  }

  send(obj) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(obj));
    }
  }

  setEco(eco) {
    this.send({ type: "set_eco", eco });
  }

  setRpm(rpm) {
    this.send({ type: "set_rpm", rpm });
  }

  _emit(type, payload) {
    const arr = this._listeners.get(type);
    if (!arr) return;
    for (const fn of arr) {
      try {
        fn(payload);
      } catch (e) {
        console.error("listener error", e);
      }
    }
  }
}
