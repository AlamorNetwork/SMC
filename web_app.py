from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from contextlib import asynccontextmanager

from ws_manager import manager
from shared_state import bot_state
from settings import settings
from backtester import SMCBacktester
from main import execute_bot_loop  # 👈 اتصال مستقیم به موتور تحلیلگر ربات

# اجرای پس‌زمینه ربات همزمان با روشن شدن وب‌سایت
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 در حال راه‌اندازی موتور اصلی ربات در پس‌زمینه سرور...")
    task = asyncio.create_task(execute_bot_loop())
    yield
    task.cancel()

app = FastAPI(title="SMC Institutional Terminal", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

if not bot_state["active_pairs"]:
    bot_state["active_pairs"] = settings.WATCHLIST.copy()

class WatchlistRequest(BaseModel):
    symbol: str

class BacktestRequest(BaseModel):
    symbol: str
    limit: int = 1000

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/api/watchlist")
async def get_watchlist():
    return {"watchlist": bot_state["active_pairs"]}

@app.post("/api/watchlist/add")
async def add_to_watchlist(req: WatchlistRequest):
    symbol = req.symbol.upper()
    if symbol not in bot_state["active_pairs"]:
        bot_state["active_pairs"].append(symbol)
    return {"status": "success", "watchlist": bot_state["active_pairs"]}

@app.post("/api/watchlist/remove")
async def remove_from_watchlist(req: WatchlistRequest):
    symbol = req.symbol.upper()
    if symbol in bot_state["active_pairs"]:
        bot_state["active_pairs"].remove(symbol)
        if symbol in bot_state["market_data"]:
            del bot_state["market_data"][symbol]
    return {"status": "success", "watchlist": bot_state["active_pairs"]}

@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    try:
        tester = SMCBacktester()
        results = await asyncio.to_thread(tester.run_backtest, [req.symbol.upper()], req.limit)
        if results:
            return {"status": "success", "data": results[0]}
        return {"status": "error", "message": "دیتای کافی یافت نشد"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket): # 👈 کلمه : WebSocket اضافه شد
    try:
        await manager.connect(websocket)
        while True:
            # این خط اتصال را زنده نگه می‌دارد
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ اتصال کلاینت قطع شد: {e}")
        manager.disconnect(websocket)