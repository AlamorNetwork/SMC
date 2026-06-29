import pandas as pd
import numpy as np

class MarketStructureAnalyzer:
    @staticmethod
    def detect_swings(df, n=2):
        df = df.copy()
        df['swing_high'] = np.nan
        df['swing_low'] = np.nan
        
        for i in range(n, len(df) - n):
            is_high = True
            for j in range(1, n + 1):
                if df['high'].iloc[i] <= df['high'].iloc[i-j] or df['high'].iloc[i] <= df['high'].iloc[i+j]:
                    is_high = False
                    break
            if is_high:
                df.iloc[i, df.columns.get_loc('swing_high')] = df['high'].iloc[i]
                
            is_low = True
            for j in range(1, n + 1):
                if df['low'].iloc[i] >= df['low'].iloc[i-j] or df['low'].iloc[i] >= df['low'].iloc[i+j]:
                    is_low = False
                    break
            if is_low:
                df.iloc[i, df.columns.get_loc('swing_low')] = df['low'].iloc[i]
        return df

    def analyze_structure(self, df_h4):
        df = self.detect_swings(df_h4)
        trend = "Neutral"
        last_break_type = None 
        main_leg = {"start": None, "start_time": None, "end": None, "end_time": None, "direction": None}
        
        highs = df[df['swing_high'].notna()]
        lows = df[df['swing_low'].notna()]
        
        if len(highs) < 2 or len(lows) < 2:
            return trend, main_leg, last_break_type
            
        current_close = df['close'].iloc[-1]
        
        if highs['high'].iloc[-1] > highs['high'].iloc[-2] and lows['low'].iloc[-1] > lows['low'].iloc[-2]:
            trend = "Bullish"
        elif highs['high'].iloc[-1] < highs['high'].iloc[-2] and lows['low'].iloc[-1] < lows['low'].iloc[-2]:
            trend = "Bearish"
            
        # بازنویسی منطق الگوریتم طبق SMC: پیدا کردن بازوی حرکتی از آخرین نقطه سوئینگ معتبر
        if current_close > highs['high'].iloc[-2]:
            last_break_type = "BOS"
            trend = "Bullish"
            start_val = lows['low'].iloc[-1]
            start_time = lows.index[-1]
            df_after_start = df.loc[start_time:]
            end_val = df_after_start['high'].max()
            end_time = df_after_start['high'].idxmax()
            main_leg = {"start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, "direction": "Bullish"}
            
        elif current_close < lows['low'].iloc[-2]:
            last_break_type = "MSS"
            trend = "Bearish"
            start_val = highs['high'].iloc[-1]
            start_time = highs.index[-1]
            df_after_start = df.loc[start_time:]
            end_val = df_after_start['low'].min()
            end_time = df_after_start['low'].idxmin()
            main_leg = {"start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, "direction": "Bearish"}
        else:
            if trend == "Bullish":
                start_val = lows['low'].iloc[-1]
                start_time = lows.index[-1]
                df_after_start = df.loc[start_time:]
                end_val = df_after_start['high'].max()
                end_time = df_after_start['high'].idxmax()
                main_leg = {"start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, "direction": "Bullish"}
            else:
                start_val = highs['high'].iloc[-1]
                start_time = highs.index[-1]
                df_after_start = df.loc[start_time:]
                end_val = df_after_start['low'].min()
                end_time = df_after_start['low'].idxmin()
                main_leg = {"start": start_val, "start_time": start_time, "end": end_val, "end_time": end_time, "direction": "Bearish"}
                
        return trend, main_leg, last_break_type