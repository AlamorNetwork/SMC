import ccxt
import pandas as pd
import time
import os

def download_massive_history(symbol, timeframe, total_candles=10000):
    print(f"🚀 شروع دانلود {total_candles} کندل برای {symbol} در تایم‌فریم {timeframe}...")
    
    # استفاده از صرافی بایننس برای دیتای رایگان بدون قطعی
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap' # گرفتن دیتای بازار فیوچرز
        }
    })
    
    # تبدیل تایم‌فریم به میلی‌ثانیه برای محاسبات ریاضی زمان
    tf_ms = exchange.parse_timeframe(timeframe) * 1000
    now = exchange.milliseconds()
    
    # محاسبه زمان شروع (مثلاً ۳۰ هزار کندل ۴ ساعته یعنی سال‌ها پیش!)
    since = now - (total_candles * tf_ms)
    
    all_candles = []
    
    # حلقه Pagination (درخواست‌های ۱۰۰۰ تایی پشت سر هم)
    while len(all_candles) < total_candles:
        try:
            # دریافت ۱۰۰۰ کندل از زمان 'since'
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            
            if not candles:
                break
                
            all_candles.extend(candles)
            
            # تنظیم زمان (since) برای درخواست بعدی: زمان آخرین کندل دریافت‌شده + یک کندل
            since = candles[-1][0] + tf_ms 
            
            print(f"📥 تا الان {len(all_candles)} کندل دریافت شد...")
            time.sleep(0.5) # استراحت نیم‌ثانیه‌ای برای جلوگیری از مسدود شدن IP توسط بایننس
            
            # اگر زمان به امروز رسید، حلقه را متوقف کن
            if since >= now:
                break
                
        except Exception as e:
            print(f"❌ خطا در دریافت دیتا: {e}")
            print("⏳ ۵ ثانیه صبر می‌کنیم و دوباره تلاش می‌کنیم...")
            time.sleep(5)
            
    # تبدیل لیست داده‌ها به DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # حذف کندل‌های تکراری (برای اطمینان از سلامت دیتابیس)
    df = df[~df.index.duplicated(keep='first')]
    
    # ذخیره دیتا با همان فرمت و نامی که ربات ما نیاز دارد
    safe_symbol = symbol.replace("/", "_").replace(":", "_")
    filename = f"data_{safe_symbol}_{timeframe}.csv"
    df.to_csv(filename)
    
    print(f"✅ فایل {filename} با {len(df)} کندل با موفقیت ساخته شد!\n")

if __name__ == "__main__":
    # در اینجا می‌توانی نماد و تعداد کندلی که می‌خواهی را مشخص کنی
    target_symbol = "BTC/USDT"
    
    # دانلود تاریخچه برای ساختار (H4) و تاییدیه (M15)
    # برای تست، 10 هزار کندل می‌گیریم (میتوانی روی 30000 تنظیم کنی)
    download_massive_history(target_symbol, "4h", 10000)
    download_massive_history(target_symbol, "15m", 10000)