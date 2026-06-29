import pandas as pd
import numpy as np

class MarketStructureAnalyzer:
    @staticmethod
    def detect_swings(df, n=3):
        """
        پیدا کردن سقف و کف‌های ماژور و معتبر بازار با بررسی شمع‌های قبل و بعد
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

    def check_inducement(self, df, ob_timestamp, direction):
        """
        بررسی وجود القا (Inducement) بر اساس تئوری فرانک میلر.
        آیا بازار قبل از بازگشت به اوردربلاک، نقدینگی خرد داخلی (Minor) مهندسی کرده است؟
        """
        try:
            df_after_ob = df.loc[ob_timestamp:]
            if len(df_after_ob) < 2:
                return False
                
            # بررسی هوشمند پویای حرکت قیمت بعد از بلاک سفارش
            if direction == "Bullish":
                for i in range(1, len(df_after_ob) - 1):
                    current_low = df_after_ob['low'].iloc[i]
                    # تشکیل یک کف فرعی (Minor Low) بالاتر از محدوده OB
                    if current_low < df_after_ob['low'].iloc[i-1] and current_low < df_after_ob['low'].iloc[i+1]:
                        if current_low > df_after_ob['high'].iloc[0]:
                            return True
            else:
                for i in range(1, len(df_after_ob) - 1):
                    current_high = df_after_ob['high'].iloc[i]
                    # تشکیل یک سقف فرعی (Minor High) پایین‌تر از محدوده OB
                    if current_high > df_after_ob['high'].iloc[i-1] and current_high > df_after_ob['high'].iloc[i+1]:
                        if current_high < df_after_ob['low'].iloc[0]:
                            return True
                            
            # فیلتر کمکی: اگر بیش از ۳ کندل گذشته باشد، بازار ساختار داخلی رنج برای القا ایجاد کرده است
            return len(df_after_ob) > 3
        except:
            return False

    def analyze_structure(self, df_h4):
        """
        موتور ردیابی وضعیت ساختار بازار (Institutional Structure State Tracker)
        این متد روند تثبیت شده را در حین اصلاح‌ها و پولبک‌ها حفظ می‌کند.
        """
        df = self.detect_swings(df_h4, n=3)
        trend = "Neutral"
        last_break_type = None 
        
        main_leg = {
            "start": None, "start_time": None, "end": None, "end_time": None, 
            "direction": None, "is_valid": False, "validation_notes": []
        }
        
        high_indices = df[df['swing_high'].notna()].index
        low_indices = df[df['swing_low'].notna()].index
        
        # برای تحلیل ساختار، حداقل نیاز به ۲ سقف و کف ماژور تاریخی داریم
        if len(high_indices) < 2 or len(low_indices) < 2:
            return trend, main_leg, last_break_type
            
        # مقادیر اولیه برای ردیابی زنده سقف و کف‌های فعال فعال
        active_high = df.loc[high_indices[0], 'high']
        active_high_time = high_indices[0]
        active_low = df.loc[low_indices[0], 'low']
        active_low_time = low_indices[0]
        
        # شبیه‌سازی گام‌به‌گام تحویل قیمت توسط جریان سفارشات نهادی
        for idx, row in df.iterrows():
            if idx in high_indices:
                active_high = row['swing_high']
                active_high_time = idx
            if idx in low_indices:
                active_low = row['swing_low']
                active_low_time = idx
                
            # شرط صعودی: بسته‌شدن بدنه کندل بالاتر از آخرین سقف ماژور فعال
            if trend != "Bullish" and row['close'] > active_high and idx > active_high_time:
                last_break_type = "CHoCH" if trend == "Bearish" else "BOS"
                trend = "Bullish"
                
                start_val = active_low
                start_time = active_low_time
                
                df_since_start = df.loc[start_time:idx]
                end_val = df_since_start['high'].max()
                end_time = df_since_start['high'].idxmax()
                
                main_leg = {
                    "start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, 
                    "direction": "Bullish", "is_valid": True, 
                    "validation_notes": [f"✅ روند صعودی فعال با شکست {last_break_type}"]
                }
                
            # شرط نزولی: بسته‌شدن بدنه کندل پایین‌تر از آخرین کف ماژور فعال
            elif trend != "Bearish" and row['close'] < active_low and idx > active_low_time:
                last_break_type = "CHoCH" if trend == "Bullish" else "MSS"
                trend = "Bearish"
                
                start_val = active_high
                start_time = active_high_time
                
                df_since_start = df.loc[start_time:idx]
                end_val = df_since_start['low'].min()
                end_time = df_since_start['low'].idxmin()
                
                main_leg = {
                    "start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, 
                    "direction": "Bearish", "is_valid": True, 
                    "validation_notes": [f"✅ روند نزولی فعال با شکست {last_break_type}"]
                }
            
            # بروزرسانی پویا و زنده بالاترین/پایین‌ترین نقطه لگ در حین پیشروی بازار
            if trend == "Bullish" and main_leg["start_time"] is not None:
                df_since_start = df.loc[main_leg["start_time"]:idx]
                main_leg["end"] = df_since_start['high'].max()
                main_leg["end_time"] = df_since_start['high'].idxmax()
                
            elif trend == "Bearish" and main_leg["start_time"] is not None:
                df_since_start = df.loc[main_leg["start_time"]:idx]
                main_leg["end"] = df_since_start['low'].min()
                main_leg["end_time"] = df_since_start['low'].idxmin()

        return trend, main_leg, last_break_type