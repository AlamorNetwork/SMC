import pandas as pd
import numpy as np

class MarketStructureAnalyzer:
    @staticmethod
    def detect_swings(df, n=3):
        """ پیدا کردن سقف و کف‌های ماژور (اصلی) """
        df = df.copy()
        df['swing_high'] = np.nan
        df['swing_low'] = np.nan
        
        for i in range(n, len(df) - n):
            if df['high'].iloc[i] == df['high'].iloc[i-n:i+n+1].max():
                df.iloc[i, df.columns.get_loc('swing_high')] = df['high'].iloc[i]
            if df['low'].iloc[i] == df['low'].iloc[i-n:i+n+1].min():
                df.iloc[i, df.columns.get_loc('swing_low')] = df['low'].iloc[i]
        return df

    def check_inducement(self, df, ob_timestamp, direction):
        """
        آموزش کد: بررسی وجود القا (Inducement) پیش از اوردربلاک.
        القا یعنی قیمت بعد از ساخت اوردربلاک، یک سقف یا کف فرعی (Minor) بسازد تا معامله‌گران عجول را فریب دهد.
        """
        # جدا کردن دیتاهایی که دقیقاً بعد از زمان تشکیل اوردربلاک ثبت شده‌اند
        df_after_ob = df.loc[ob_timestamp:]
        if len(df_after_ob) < 5:
            return False
            
        # پیدا کردن سقف/کف‌های کوچک‌تر (n=2)
        swings = self.detect_swings(df_after_ob, n=2)
        
        if direction == "Bullish":
            # برای خرید: آیا بعد از اوردربلاک، کف‌های فرعی (تله) تشکیل شده است؟
            minor_lows = swings[swings['swing_low'].notna()]
            return len(minor_lows) >= 1
        else:
            # برای فروش: آیا بعد از اوردربلاک، سقف‌های فرعی (تله) تشکیل شده است؟
            minor_highs = swings[swings['swing_high'].notna()]
            return len(minor_highs) >= 1

    def analyze_structure(self, df_h4):
        """ تشخیص روند اصلی بازار و لگ حرکتی معتبر """
        df = self.detect_swings(df_h4, n=3)
        trend = "Neutral"
        last_break_type = None 
        
        main_leg = {
            "start": None, "start_time": None, "end": None, "end_time": None, 
            "direction": None, "is_valid": False, "validation_notes": []
        }
        
        highs = df[df['swing_high'].notna()]
        lows = df[df['swing_low'].notna()]
        
        if len(highs) < 3 or len(lows) < 3:
            return trend, main_leg, last_break_type
            
        current_close = df['close'].iloc[-1]
        
        last_high_idx = highs.index[-1]
        last_high_val = highs['high'].iloc[-1]
        prev_high_val = highs['high'].iloc[-2]
        
        last_low_idx = lows.index[-1]
        last_low_val = lows['low'].iloc[-1]
        prev_low_val = lows['low'].iloc[-2]
        
        # --- لگ صعودی ---
        if current_close > last_high_val:
            trend = "Bullish"
            last_break_type = "BOS"
            start_time, start_val = last_low_idx, last_low_val
            end_val = df.loc[start_time:]['high'].max()
            end_time = df.loc[start_time:]['high'].idxmax()
            
            swept = start_val < prev_low_val
            
            main_leg = {
                "start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, 
                "direction": "Bullish", "is_valid": swept, "validation_notes": ["✅ شکست ساختار (BOS)"]
            }
            
        # --- لگ نزولی ---
        elif current_close < last_low_val:
            trend = "Bearish"
            last_break_type = "MSS"
            start_time, start_val = last_high_idx, last_high_val
            end_val = df.loc[start_time:]['low'].min()
            end_time = df.loc[start_time:]['low'].idxmin()
            
            swept = start_val > prev_high_val
            
            main_leg = {
                "start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, 
                "direction": "Bearish", "is_valid": swept, "validation_notes": ["✅ شکست ساختار (MSS)"]
            }
            
        return trend, main_leg, last_break_type