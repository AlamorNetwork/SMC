import os
import ccxt
import pandas as pd
from settings import settings

class DataFetcher:
    def __init__(self):
        self.exchange = ccxt.toobit({
            'apiKey': settings.TOOBIT_API_KEY,
            'secret': settings.TOOBIT_SECRET_KEY,
            'enableRateLimit': True,
        })
        
    def get_candles(self, symbol, timeframe, limit=200):
        # ساخت نام فایل امن برای ذخیره آفلاین دیتای هر ارز
        safe_symbol = symbol.replace("/", "_")
        filename = f"data_{safe_symbol}_{timeframe}.csv"
        
        # قانون جدید: اگر فایل آفلاین وجود دارد، از روی هارد سرور بخوان تا به API درخواست نزند!
        if os.path.exists(filename):
            df = pd.read_csv(filename, index_col='timestamp', parse_dates=True)
            return df
            
        # اگر فایل نبود، فقط برای بار اول دانلود و ذخیره کند
        try:
            print(f"   🌐 دریافت آنلاین داده‌های {symbol} از API صرافی و ذخیره آفلاین...")
            raw_candles = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not raw_candles:
                return None
                
            df = pd.DataFrame(raw_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            # ذخیره در فایل اکسل/CSV برای استفاده‌های آفلاین بعدی
            df.to_csv(filename)
            return df
        except Exception as e:
            print(f"❌ خطا در دریافت آنلاین دیتای {symbol}: {e}")
            return None

    def fetch_all_required_data(self, symbol):
        df_h4 = self.get_candles(symbol, settings.TIMEFRAME_STRUCTURE, limit=150)
        df_m15 = self.get_candles(symbol, settings.TIMEFRAME_ENTRY, limit=200)
        return df_h4, df_m15