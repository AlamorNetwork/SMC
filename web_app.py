from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from settings import settings

app = FastAPI(title="SMC Bot Panel")

# تنظیم پوشه قالب‌های HTML
templates = Jinja2Templates(directory="templates")

def verify_cookie(request: Request):
    """بررسی می‌کند که آیا کاربر لاگین کرده است یا خیر"""
    if request.cookies.get("auth_session") != "authenticated":
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return True

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    # چک کردن یوزر و پسورد با فایل .env
    if username == settings.WEB_USERNAME and password == settings.WEB_PASSWORD:
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        # تنظیم کوکی برای ورود موفق (برای 24 ساعت)
        response.set_cookie(key="auth_session", value="authenticated", max_age=86400)
        return response
    
    # اگر اشتباه بود، دوباره صفحه لاگین را با ارور نشان بده
    return templates.TemplateResponse("login.html", {"request": request, "error": "نام کاربری یا رمز عبور اشتباه است."})

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("auth_session")
    return response

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(verify_cookie)])
async def dashboard(request: Request):
    # در اینجا بعداً دیتای لایو ربات را پاس می‌دهیم
    bot_status = "Online"
    active_pairs = settings.WATCHLIST
    return templates.TemplateResponse("dashboard.html", {"request": request, "bot_status": bot_status, "pairs": active_pairs})