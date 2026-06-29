import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from settings import settings

from main import execute_bot_loop
from shared_state import bot_state
from ws_manager import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🌐 راه‌اندازی سرور وب و موتور SMC...")
    # اجرای حلقه ربات به عنوان یک تسک ناهمگام در پس‌زمینه
    asyncio.create_task(execute_bot_loop())
    yield
    print("🛑 سرور خاموش شد.")

app = FastAPI(title="SMC Bot Panel", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# --- تنظیمات لاگین همانند قبل سر جایش است ---
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

# --- مسیر اصلی داشبورد ---
@app.get("/", response_class=HTMLResponse, dependencies=[Depends(verify_cookie)])
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        # مقادیر اولیه هنگام لود صفحه
        context={"state": bot_state}
    )

# --- مسیر ارتباط لایو وب‌سوکت ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # منتظر می‌ماند اما هیچ دیتایی از کلاینت نمی‌گیرد (ارتباط یک‌طرفه سرور به فرانت)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)