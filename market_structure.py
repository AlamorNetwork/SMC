import pandas as pd
import numpy as np

class MarketStructureAnalyzer:
    def map_true_structure(self, df, atr_window=14, atr_multiplier=1.5):
        df = df.copy()
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
        
        trend = 1 
        for i in range(1, len(df)):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_atr = df['atr'].iloc[i]
            
            if pd.isna(current_atr): continue
                
            if trend == 1:
                if current_high > last_high_val:
                    last_high_val = current_high
                    last_high_idx = df.index[i]
                elif current_high < last_high_val - (current_atr * atr_multiplier):
                    df.loc[last_high_idx, 'macro_high'] = last_high_val
                    trend = -1
                    last_low_val = current_low
                    last_low_idx = df.index[i]
                    
            elif trend == -1:
                if current_low < last_low_val:
                    last_low_val = current_low
                    last_low_idx = df.index[i]
                elif current_low > last_low_val + (current_atr * atr_multiplier):
                    df.loc[last_low_idx, 'macro_low'] = last_low_val
                    trend = 1
                    last_high_val = current_high
                    last_high_idx = df.index[i]
        return df

    def extract_historical_legs(self, df_h4):
        """
        این متد کل تاریخچه (مثلا ۱۰ هزار کندل) را بررسی می‌کند و
        تمام BOS و CHoCH ها را به صورت یک تایم‌لاین برای داشبورد برمی‌گرداند.
        """
        df = self.map_true_structure(df_h4)
        trend = "Neutral"
        history = []
        
        high_indices = df[df['macro_high'].notna()].index
        low_indices = df[df['macro_low'].notna()].index
        
        if len(high_indices) < 1 or len(low_indices) < 1: return []
            
        active_high = df.loc[high_indices[0], 'high']
        active_high_time = high_indices[0]
        active_low = df.loc[low_indices[0], 'low']
        active_low_time = low_indices[0]
        
        last_broken_high_time = None
        last_broken_low_time = None
        
        for idx, row in df.iterrows():
            if idx in high_indices:
                active_high = row['macro_high']
                active_high_time = idx
            if idx in low_indices:
                active_low = row['macro_low']
                active_low_time = idx
                
            # 🚀 بهینه‌سازی: ثبت تمام BOS های متوالی (حل باگ قبلی)
            if row['close'] > active_high and idx > active_high_time:
                if last_broken_high_time != active_high_time:
                    break_type = "CHoCH" if trend == "Bearish" or trend == "Neutral" else "BOS"
                    trend = "Bullish"
                    history.append({
                        "time": str(idx), "type": break_type, "direction": "Bullish",
                        "break_price": round(active_high, 4), "start_leg_time": str(active_low_time),
                        "start_leg_price": round(active_low, 4)
                    })
                    last_broken_high_time = active_high_time
                    
            elif row['close'] < active_low and idx > active_low_time:
                if last_broken_low_time != active_low_time:
                    break_type = "CHoCH" if trend == "Bullish" or trend == "Neutral" else "BOS"
                    trend = "Bearish"
                    history.append({
                        "time": str(idx), "type": break_type, "direction": "Bearish",
                        "break_price": round(active_low, 4), "start_leg_time": str(active_high_time),
                        "start_leg_price": round(active_high, 4)
                    })
                    last_broken_low_time = active_low_time

        history.reverse() # جدیدترین‌ها در ابتدا
        return history

    def check_inducement(self, df, ob_timestamp, direction):
        try:
            df_after_ob = df.loc[ob_timestamp:]
            if len(df_after_ob) < 2: return False
                
            if direction == "Bullish":
                for i in range(1, len(df_after_ob) - 1):
                    current_low = df_after_ob['low'].iloc[i]
                    if current_low < df_after_ob['low'].iloc[i-1] and current_low < df_after_ob['low'].iloc[i+1]:
                        if current_low > df_after_ob['high'].iloc[0]: return True
            else:
                for i in range(1, len(df_after_ob) - 1):
                    current_high = df_after_ob['high'].iloc[i]
                    if current_high > df_after_ob['high'].iloc[i-1] and current_high > df_after_ob['high'].iloc[i+1]:
                        if current_high < df_after_ob['low'].iloc[0]: return True
            return len(df_after_ob) > 3
        except: return False

    def analyze_structure(self, df_h4):
        df = self.map_true_structure(df_h4)
        trend = "Neutral"
        last_break_type = None 
        main_leg = {
            "start": None, "start_time": None, "end": None, "end_time": None, 
            "direction": None, "is_valid": False, "validation_notes": [],
            "last_macro_high": None, "last_macro_low": None
        }
        
        high_indices = df[df['macro_high'].notna()].index
        low_indices = df[df['macro_low'].notna()].index
        if len(high_indices) < 2 or len(low_indices) < 2: return trend, main_leg, last_break_type
            
        active_high = df.loc[high_indices[0], 'high']; active_high_time = high_indices[0]
        active_low = df.loc[low_indices[0], 'low']; active_low_time = low_indices[0]
        last_broken_high_time = None; last_broken_low_time = None
        
        for idx, row in df.iterrows():
            if idx in high_indices:
                active_high = row['macro_high']; active_high_time = idx
            if idx in low_indices:
                active_low = row['macro_low']; active_low_time = idx
                
            if row['close'] > active_high and idx > active_high_time and last_broken_high_time != active_high_time:
                last_break_type = "CHoCH" if trend == "Bearish" else "BOS"
                trend = "Bullish"; last_broken_high_time = active_high_time
                main_leg.update({
                    "start": active_low, "start_time": active_low_time, 
                    "end": df.loc[active_low_time:idx]['high'].max(), "end_time": df.loc[active_low_time:idx]['high'].idxmax(), 
                    "direction": "Bullish", "is_valid": True, "last_macro_high": active_high, "last_macro_low": active_low
                })
                
            elif row['close'] < active_low and idx > active_low_time and last_broken_low_time != active_low_time:
                last_break_type = "CHoCH" if trend == "Bullish" else "BOS"
                trend = "Bearish"; last_broken_low_time = active_low_time
                main_leg.update({
                    "start": active_high, "start_time": active_high_time, 
                    "end": df.loc[active_high_time:idx]['low'].min(), "end_time": df.loc[active_high_time:idx]['low'].idxmin(), 
                    "direction": "Bearish", "is_valid": True, "last_macro_high": active_high, "last_macro_low": active_low
                })
            
            if trend == "Bullish" and main_leg["start_time"] is not None:
                df_since_start = df.loc[main_leg["start_time"]:idx]
                main_leg["end"] = df_since_start['high'].max(); main_leg["end_time"] = df_since_start['high'].idxmax()
                main_leg["last_macro_low"] = active_low
            elif trend == "Bearish" and main_leg["start_time"] is not None:
                df_since_start = df.loc[main_leg["start_time"]:idx]
                main_leg["end"] = df_since_start['low'].min(); main_leg["end_time"] = df_since_start['low'].idxmin()
                main_leg["last_macro_high"] = active_high

        return trend, main_leg, last_break_type