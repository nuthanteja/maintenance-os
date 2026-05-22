import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...streaming.manager import StreamClient, get_stream_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stream"])


@router.websocket("/ws/stream")
async def stream_ws(ws: WebSocket) -> None:
    await ws.accept()
    mgr = get_stream_manager()
    client = StreamClient(ws=ws)
    await mgr.add_client(client)

    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")
            if mtype == "set_eco":
                client.eco_mode = bool(msg.get("eco", False))
                await client.send_json({"type": "status", "eco_mode": client.eco_mode})
            elif mtype == "set_rpm":
                rpm = float(msg.get("rpm", mgr.rpm))
                await mgr.set_rpm(rpm)
            elif mtype == "ping":
                await client.send_json({"type": "pong"})
            else:
                await client.send_json({"type": "error", "message": f"unknown type: {mtype!r}"})
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws handler crashed")
    finally:
        await mgr.remove_client(client)
