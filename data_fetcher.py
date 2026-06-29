import os
import ccxt
import pandas as pd
from settings import settings

class DataFetcher:
    def __init__(self):
        # اضافه کردن تنظیمات فیوچرز به ccxt
        self.exchange = ccxt.toobit({
            'apiKey': settings.TOOBIT_API_KEY,
            'secret': settings.TOOBIT_SECRET_KEY,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # 🚀 این خط ربات را به مارکت فیوچرز متصل می‌کند
            }
        })
        
    def get_candles(self, symbol, timeframe, limit=200):
        # ساخت نام فایل امن برای ذخیره آفلاین دیتای هر ارز
        safe_symbol = symbol.replace("/", "_").replace(":", "_") # فرمت نام فایل برای فیوچرز
        filename = f"data_{safe_symbol}_{timeframe}.csv"
        
        if os.path.exists(filename):
            df = pd.read_csv(filename, index_col='timestamp', parse_dates=True)
            return df
            
        try:
            print(f"   🌐 دریافت آنلاین داده‌های فیوچرز {symbol}...")
            # در مارکت فیوچرز نمادها معمولاً به شکل متعارف ccxt فراخوانی می‌شوند
            raw_candles = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not raw_candles:
                return None
                
            df = pd.DataFrame(raw_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            df.to_csv(filename)
            return df
        except Exception as e:
            print(f"❌ خطا در دریافت آنلاین دیتای فیوچرز {symbol}: {e}")
            return None

    def fetch_all_required_data(self, symbol):
        df_h4 = self.get_candles(symbol, settings.TIMEFRAME_STRUCTURE, limit=150)
        df_m15 = self.get_candles(symbol, settings.TIMEFRAME_ENTRY, limit=200)
        return df_h4, df_m15
    
    def get_current_price(self, symbol):
        """
        آموزش کد: این تابع فقط قیمت لحظه‌ای (Live Price) را از صرافی می‌گیرد.
        این درخواست بسیار سبک است و می‌توان آن را هر ثانیه صدا زد بدون اینکه صرافی ما را مسدود کند.
        """
        try:
            # گرفتن دیتای تیکر (قیمت فعلی بازار)
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            print(f"❌ خطا در دریافت قیمت لایو {symbol}: {e}")
            return None