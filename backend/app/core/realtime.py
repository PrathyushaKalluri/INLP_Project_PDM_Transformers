import json
from collections import defaultdict

from fastapi import WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(user_id, None)

    async def emit_to_user(self, user_id: str, event_type: str, payload: dict) -> None:
        message = json.dumps({"type": event_type, "payload": payload}, default=str)
        stale: list[WebSocket] = []
        for ws in self._connections.get(user_id, set()):
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(user_id, ws)

    async def emit_to_users(self, user_ids: list[str], event_type: str, payload: dict) -> None:
        for user_id in user_ids:
            await self.emit_to_user(user_id, event_type, payload)


realtime_hub = RealtimeHub()
