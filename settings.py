import os
from dotenv import load_dotenv

# لود کردن فایل .env از روت پروژه
load_dotenv()

class Settings:
    TOOBIT_API_KEY = os.getenv("TOOBIT_API_KEY", "")
    TOOBIT_SECRET_KEY = os.getenv("TOOBIT_SECRET_KEY", "")
    
    # واچ‌لیست ارزها برای رصد همزمان
    WATCHLIST = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
    
    # تایم‌فریم‌های استراتژی SMC
    TIMEFRAME_STRUCTURE = "4h"  # تایم‌فریم ساختار اصلی (H4)
    TIMEFRAME_ENTRY = "15m"      # تایم‌فریم ورود و تاییدیه (M15)
    
    # تنظیمات ریسک و سرمایه
    RISK_PERCENT = 1.0          # درصد ریسک ثابت از کل سرمایه برای هر معامله (1%)
    MAX_CONCURRENT_TRADES = 3   # حداکثر تعداد پوزیشن‌های همزمان
    
    # فیلترهای حجمی و فنی
    VOLUME_MULTIPLIER_IMPULSE = 1.5  # ضریب حجم برای تشخیص حرکت قدرتمند (Impulse)
    VOLUME_MULTIPLIER_ENTRY = 1.2    # ضریب حجم برای تاییدیه کندل ورود در M15
    
    # فیبوناچی OTE (Optimal Trade Entry)
    FIB_OTE_LOW = 0.71
    FIB_OTE_HIGH = 0.79

settings = Settings()