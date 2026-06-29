import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from settings import settings

# ایمپورت کردن موتور ربات و حافظه مشترک
from main import execute_bot_loop
from shared_state import bot_state

# این بخش ربات را هنگام روشن شدن پنل وب استارت می‌زند
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🌐 پنل وب در حال روشن شدن است...")
    # روشن کردن موتور اصلی ربات در یک پردازش موازی (Background Thread)
    bot_thread = threading.Thread(target=execute_bot_loop, daemon=True)
    bot_thread.start()
    yield
    print("🛑 سرور وب خاموش شد.")

app = FastAPI(title="SMC Bot Panel", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

def verify_cookie(request: Request):
    if request.cookies.get("auth_session") != "authenticated":
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return True

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})

@app.post("/login")
async def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == settings.WEB_USERNAME and password == settings.WEB_PASSWORD:
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="auth_session", value="authenticated", max_age=86400)
        return response
    return templates.TemplateResponse(request=request, name="login.html", context={"error": "نام کاربری یا رمز عبور اشتباه است."})

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("auth_session")
    return response

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(verify_cookie)])
async def dashboard(request: Request):
    # دیتا را از حافظه مشترک می‌خوانیم و به HTML پاس می‌دهیم
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={
            "bot_status": bot_state["status"],
            "pairs": bot_state["active_pairs"],
            "signals_today": bot_state["signals_today"],
            "open_positions": bot_state["open_positions"],
            "total_pnl": bot_state["total_pnl"],
            "last_update": bot_state["last_update"]
        }
    )