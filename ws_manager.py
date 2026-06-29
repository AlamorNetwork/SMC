from fastapi import WebSocket
from typing import List

class ConnectionManager:
    def __init__(self):
        # لیستی از تمام تب‌ها و مرورگرهای متصل به پنل
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # ارسال دیتای جدید به صورت JSON برای تمام کاربران متصل
        for connection in self.active_connections:
            await connection.send_json(message)

# ساخت یک نمونه از منیجر برای استفاده در کل پروژه
manager = ConnectionManager()