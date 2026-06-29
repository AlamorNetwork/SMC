# خط ایمپورت‌های بالا را به این شکل کامل کن:
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
from ws_manager import manager
from shared_state import bot_state
from settings import settings
from backtester import SMCBacktester # فراخوانی موتور بک‌تست
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="SMC Institutional Terminal")

# 🚀 اضافه شدن تنظیمات CORS برای رفع خطای 403 وب‌سوکت
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # اجازه اتصال به همه IP ها و دامنه‌ها
    allow_credentials=True,
    allow_methods=["*"],  # اجازه همه متدها (GET, POST, WS و ...)
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# مقداردهی اولیه واچ‌لیست در مموری
if not bot_state["active_pairs"]:
    bot_state["active_pairs"] = settings.WATCHLIST.copy()
# ---- مدل‌های دیتا برای API ----
class WatchlistRequest(BaseModel):
    symbol: str

class BacktestRequest(BaseModel):
    symbol: str
    limit: int = 1000

# ---- صفحات وب ----
# ---- صفحات وب ----
@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    # به جای پاس دادن مستقیم، از آرگومان‌های نام‌گذاری شده (request= و name=) استفاده می‌کنیم
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html"
    )

# ---- API های واچ‌لیست ----
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
        # پاک کردن دیتای آن از داشبورد
        if symbol in bot_state["market_data"]:
            del bot_state["market_data"][symbol]
    return {"status": "success", "watchlist": bot_state["active_pairs"]}

# ---- API موتور بک‌تست ----
@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    try:
        tester = SMCBacktester()
        # اجرای بک‌تست در یک ترد جداگانه تا سرور قفل نشود
        results = await asyncio.to_thread(tester.run_backtest, [req.symbol.upper()], req.limit)
        if results:
            return {"status": "success", "data": results[0]}
        return {"status": "error", "message": "دیتای کافی یافت نشد"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ---- وب‌سوکت برای دیتای لایو ----
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await manager.connect(websocket)
        while True:
            # منتظر ماندن برای دریافت پیام از کلاینت (برای باز نگه داشتن اتصال)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ خطای پیش‌بینی نشده در وب‌سوکت: {e}")
        manager.disconnect(websocket)