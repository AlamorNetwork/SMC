from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
from ws_manager import manager
from shared_state import bot_state
from settings import settings
from backtester import SMCBacktester # فراخوانی موتور بک‌تست

app = FastAPI(title="SMC Institutional Terminal")
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
@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

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

# وب‌سوکت برای دیتای لایو (کدهای قبلی سرجایش است)
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        manager.disconnect(websocket)