import pandas as pd
import numpy as np

class MarketStructureAnalyzer:
    def map_true_structure(self, df, atr_window=14, atr_multiplier=1.5):
        """
        این الگوریتم به جای زمان (تعداد کندل)، از نوسانات واقعی بازار (ATR) 
        برای تشخیص سقف و کف‌های اصلی (Macro) استفاده می‌کند.
        """
        df = df.copy()
        
        # محاسبه ATR برای درک میزان نوسان طبیعی بازار
        df['tr'] = np.maximum(df['high'] - df['low'], 
                   np.maximum(abs(df['high'] - df['close'].shift(1)), 
                              abs(df['low'] - df['close'].shift(1))))
        df['atr'] = df['tr'].rolling(window=atr_window).mean()
        
        df['macro_high'] = np.nan
        df['macro_low'] = np.nan
        
        last_high_val = df['high'].iloc[0]
        last_high_idx = df.index[0]
        last_low_val = df['low'].iloc[0]
        last_low_idx = df.index[0]
        
        trend = 1 # 1 صعودی, -1 نزولی
        
        for i in range(1, len(df)):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_atr = df['atr'].iloc[i]
            
            if pd.isna(current_atr): continue
                
            # تشخیص کف ماژور (پایان اصلاح و شروع لگ جدید)
            if trend == 1:
                if current_high > last_high_val:
                    last_high_val = current_high
                    last_high_idx = i
                # اگر قیمت به اندازه ATR از سقف فاصله گرفت، یعنی یک سقف ماژور ثبت شده است
                elif current_high < last_high_val - (current_atr * atr_multiplier):
                    df.iloc[last_high_idx, df.columns.get_loc('macro_high')] = last_high_val
                    trend = -1
                    last_low_val = current_low
                    last_low_idx = i
                    
            # تشخیص سقف ماژور
            elif trend == -1:
                if current_low < last_low_val:
                    last_low_val = current_low
                    last_low_idx = i
                elif current_low > last_low_val + (current_atr * atr_multiplier):
                    df.iloc[last_low_idx, df.columns.get_loc('macro_low')] = last_low_val
                    trend = 1
                    last_high_val = current_high
                    last_high_idx = i
                    
        return df

    def check_inducement(self, df, ob_timestamp, direction):
        """
        بررسی وجود القا (Inducement) بر اساس تئوری فرانک میلر.
        """
        try:
            df_after_ob = df.loc[ob_timestamp:]
            if len(df_after_ob) < 2:
                return False
                
            if direction == "Bullish":
                for i in range(1, len(df_after_ob) - 1):
                    current_low = df_after_ob['low'].iloc[i]
                    if current_low < df_after_ob['low'].iloc[i-1] and current_low < df_after_ob['low'].iloc[i+1]:
                        if current_low > df_after_ob['high'].iloc[0]:
                            return True
            else:
                for i in range(1, len(df_after_ob) - 1):
                    current_high = df_after_ob['high'].iloc[i]
                    if current_high > df_after_ob['high'].iloc[i-1] and current_high > df_after_ob['high'].iloc[i+1]:
                        if current_high < df_after_ob['low'].iloc[0]:
                            return True
                            
            return len(df_after_ob) > 3
        except:
            return False

    def analyze_structure(self, df_h4):
        """
        موتور ردیابی وضعیت ساختار بازار با استفاده از الگوریتم داینامیک Macro Swings
        """
        df = self.map_true_structure(df_h4)
        trend = "Neutral"
        last_break_type = None 
        
        main_leg = {
            "start": None, "start_time": None, "end": None, "end_time": None, 
            "direction": None, "is_valid": False, "validation_notes": [],
            "last_macro_high": None, "last_macro_low": None  # اضافه شده برای فیلتر SMT
        }
        
        high_indices = df[df['macro_high'].notna()].index
        low_indices = df[df['macro_low'].notna()].index
        
        if len(high_indices) < 2 or len(low_indices) < 2:
            return trend, main_leg, last_break_type
            
        active_high = df.loc[high_indices[0], 'high']
        active_high_time = high_indices[0]
        active_low = df.loc[low_indices[0], 'low']
        active_low_time = low_indices[0]
        
        for idx, row in df.iterrows():
            if idx in high_indices:
                active_high = row['macro_high']
                active_high_time = idx
            if idx in low_indices:
                active_low = row['macro_low']
                active_low_time = idx
                
            if trend != "Bullish" and row['close'] > active_high and idx > active_high_time:
                last_break_type = "CHoCH" if trend == "Bearish" else "BOS"
                trend = "Bullish"
                
                start_val = active_low
                start_time = active_low_time
                
                df_since_start = df.loc[start_time:idx]
                end_val = df_since_start['high'].max()
                end_time = df_since_start['high'].idxmax()
                
                main_leg.update({
                    "start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, 
                    "direction": "Bullish", "is_valid": True, 
                    "validation_notes": [f"✅ روند صعودی فعال با شکست {last_break_type}"],
                    "last_macro_high": active_high, "last_macro_low": active_low
                })
                
            elif trend != "Bearish" and row['close'] < active_low and idx > active_low_time:
                last_break_type = "CHoCH" if trend == "Bullish" else "MSS"
                trend = "Bearish"
                
                start_val = active_high
                start_time = active_high_time
                
                df_since_start = df.loc[start_time:idx]
                end_val = df_since_start['low'].min()
                end_time = df_since_start['low'].idxmin()
                
                main_leg.update({
                    "start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, 
                    "direction": "Bearish", "is_valid": True, 
                    "validation_notes": [f"✅ روند نزولی فعال با شکست {last_break_type}"],
                    "last_macro_high": active_high, "last_macro_low": active_low
                })
            
            if trend == "Bullish" and main_leg["start_time"] is not None:
                df_since_start = df.loc[main_leg["start_time"]:idx]
                main_leg["end"] = df_since_start['high'].max()
                main_leg["end_time"] = df_since_start['high'].idxmax()
                main_leg["last_macro_low"] = active_low
                
            elif trend == "Bearish" and main_leg["start_time"] is not None:
                df_since_start = df.loc[main_leg["start_time"]:idx]
                main_leg["end"] = df_since_start['low'].min()
                main_leg["end_time"] = df_since_start['low'].idxmin()
                main_leg["last_macro_high"] = active_high

        return trend, main_leg, last_break_type