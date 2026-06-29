import pandas as pd
import numpy as np

class MarketStructureAnalyzer:
    @staticmethod
    def detect_swings(df, n=3):
        """
        برای پیدا کردن سقف و کف‌های مهم‌تر، دوره بررسی را به 3 کندل قبل و بعد (n=3) افزایش دادیم.
        """
        df = df.copy()
        df['swing_high'] = np.nan
        df['swing_low'] = np.nan
        
        for i in range(n, len(df) - n):
            if df['high'].iloc[i] == df['high'].iloc[i-n:i+n+1].max():
                df.iloc[i, df.columns.get_loc('swing_high')] = df['high'].iloc[i]
            if df['low'].iloc[i] == df['low'].iloc[i-n:i+n+1].min():
                df.iloc[i, df.columns.get_loc('swing_low')] = df['low'].iloc[i]
        return df

    def analyze_structure(self, df_h4):
        df = self.detect_swings(df_h4, n=3)
        trend = "Neutral"
        last_break_type = None 
        
        # ساختار جدید برای نگهداری وضعیت تاییدیه لگ
        main_leg = {
            "start": None, "start_time": None, "end": None, "end_time": None, 
            "direction": None, "is_valid": False, "validation_notes": []
        }
        
        highs = df[df['swing_high'].notna()]
        lows = df[df['swing_low'].notna()]
        
        if len(highs) < 3 or len(lows) < 3:
            return trend, main_leg, last_break_type
            
        current_close = df['close'].iloc[-1]
        
        # استخراج دو سقف و کف ماژور آخر
        last_high_idx = highs.index[-1]
        last_high_val = highs['high'].iloc[-1]
        prev_high_val = highs['high'].iloc[-2]
        
        last_low_idx = lows.index[-1]
        last_low_val = lows['low'].iloc[-1]
        prev_low_val = lows['low'].iloc[-2]
        
        # --- بررسی لگ صعودی (Bullish Leg) ---
        if current_close > last_high_val:
            trend = "Bullish"
            last_break_type = "BOS"
            
            start_time = last_low_idx
            start_val = last_low_val
            
            df_after_start = df.loc[start_time:]
            end_val = df_after_start['high'].max()
            end_time = df_after_start['high'].idxmax()
            
            notes = []
            # شرط 1: هانت کف مهم قبلی
            swept = start_val < prev_low_val
            notes.append("✅ کف مهم قبلی هانت شده است (Sweep)" if swept else "❌ کف قبلی هانت نشده است")
                
            # شرط 2: شروع حرکت پرقدرت (تایید حجم در نقطه شروع)
            start_idx = df.index.get_loc(start_time)
            vol_spike = False
            if start_idx < len(df) - 1:
                vol_spike = df['volume'].iloc[start_idx+1] > df['volume'].rolling(20).mean().iloc[start_idx]
            notes.append("✅ حرکت ریورس پرقدرت و پرحجم بود" if vol_spike else "❌ حجم حرکت ریورس کافی نبود")
            
            # شرط 3 و 4: تایید BOS و ساخت CHoCH جدید
            notes.append("✅ شکست ساختار (BOS/CHoCH) محرز شد")
            
            # لگ فقط در صورتی معتبر است که هانت کرده باشد و با حجم برگشته باشد
            is_valid = swept and vol_spike
            
            main_leg = {
                "start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, 
                "direction": "Bullish", "is_valid": is_valid, "validation_notes": notes
            }
            
        # --- بررسی لگ نزولی (Bearish Leg) ---
        elif current_close < last_low_val:
            trend = "Bearish"
            last_break_type = "MSS"
            
            start_time = last_high_idx
            start_val = last_high_val
            
            df_after_start = df.loc[start_time:]
            end_val = df_after_start['low'].min()
            end_time = df_after_start['low'].idxmin()
            
            notes = []
            # شرط 1: هانت سقف مهم قبلی
            swept = start_val > prev_high_val
            notes.append("✅ سقف مهم قبلی هانت شده است (Sweep)" if swept else "❌ سقف قبلی هانت نشده است")
                
            # شرط 2: شروع حرکت پرقدرت
            start_idx = df.index.get_loc(start_time)
            vol_spike = False
            if start_idx < len(df) - 1:
                vol_spike = df['volume'].iloc[start_idx+1] > df['volume'].rolling(20).mean().iloc[start_idx]
            notes.append("✅ ریزش ریورس پرقدرت و پرحجم بود" if vol_spike else "❌ حجم ریزش ریورس کافی نبود")
                    
            notes.append("✅ شکست ساختار (BOS/CHoCH) محرز شد")
            
            is_valid = swept and vol_spike
            
            main_leg = {
                "start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, 
                "direction": "Bearish", "is_valid": is_valid, "validation_notes": notes
            }
            
        return trend, main_leg, last_break_type