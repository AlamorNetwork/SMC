import ccxt
import pandas as pd
from settings import settings

class DataFetcher:
    """
    ماژول دریافت داده‌ها از صرافی Toobit
    وظیفه: دریافت کندل‌های OHLCV برای تایم‌فریم‌های H4 و M15 به صورت کاملاً تمیز و بهینه‌شده
    """
    def __init__(self):
        self.exchange = ccxt.toobit({
            'apiKey': settings.TOOBIT_API_KEY,
            'secret': settings.TOOBIT_SECRET_KEY,
            'enableRateLimit': True,
        })
        
    def get_candles(self, symbol, timeframe, limit=200):
        """
        دریافت کندل‌ها و تبدیل آن‌ها به یک DataFrame استاندارد پانداز
        """
        try:
            raw_candles = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not raw_candles:
                return None
                
            df = pd.DataFrame(raw_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # تبدیل تمام ستون‌ها به نوع داده اعشاری برای محاسبات دقیق ریاضی
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df
        except Exception as e:
            print(f"❌ Error fetching candles for {symbol} on {timeframe}: {e}")
            return None

    def fetch_all_required_data(self, symbol):
        """
        دریافت همزمان داده‌های H4 و M15 برای یک نماد معاملاتی
        """
        df_h4 = self.get_candles(symbol, settings.TIMEFRAME_STRUCTURE, limit=150)
        df_m15 = self.get_candles(symbol, settings.TIMEFRAME_ENTRY, limit=200)
        return df_h4, df_m15