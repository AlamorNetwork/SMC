from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        # این خط بسیار حیاتی است. اگر نباشد، خطای 403 دریافت می‌کنیم
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🟢 یک کلاینت متصل شد. تعداد اتصالات زنده: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"🔴 کلاینت قطع شد. تعداد اتصالات زنده: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # ارسال پیام به تمام کاربران متصل به داشبورد
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"⚠️ خطا در ارسال پیام به کلاینت: {e}")
                self.disconnect(connection)

manager = ConnectionManager()