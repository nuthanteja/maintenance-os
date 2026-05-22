"""Standalone replay client — reads a JSONL file and prints predictions
received from a running Maintenance_OS server. Useful for debugging the
WebSocket protocol without the dashboard.

Usage:
    python scripts/replay_stream.py
    python scripts/replay_stream.py --url ws://127.0.0.1:8000/ws/stream
"""
import argparse
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("websockets not installed; pip install websockets", file=sys.stderr)
    sys.exit(2)


async def listen(url: str, eco: bool) -> None:
    async with websockets.connect(url) as ws:
        if eco:
            await ws.send(json.dumps({"type": "set_eco", "eco": True}))
        async for raw in ws:
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "prediction":
                f = msg["frame"]
                print(
                    f"[{f['timestamp']:.3f}] {f['state']:<22} "
                    f"sev={f['severity']:<8} zone={f['iso_zone']} "
                    f"state_conf={f['state_confidence']:.2f} sev_conf={f['severity_confidence']:.2f}"
                )
            elif mtype == "status":
                print(f"-- status: {msg}")
            elif mtype == "error":
                print(f"-- error: {msg.get('message')}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="ws://127.0.0.1:8000/ws/stream")
    p.add_argument("--eco", action="store_true", help="suppress raw plot frames")
    args = p.parse_args()

    try:
        asyncio.run(listen(args.url, args.eco))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
