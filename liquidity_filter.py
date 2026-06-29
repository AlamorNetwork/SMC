import pandas as pd
from settings import settings

class LiquidityAndConfirmationFilter:
    def check_liquidity_sweep(self, df_h4, direction):
        if len(df_h4) < 5: return False
            
        last_candle = df_h4.iloc[-1]
        prev_highs = df_h4['high'].iloc[:-2]
        prev_lows = df_h4['low'].iloc[:-2]
        
        if direction == "Bullish":
            # بررسی Sweep در کف‌ها (Sell Stops)
            lowest_low = prev_lows.min()
            if last_candle['low'] < lowest_low and last_candle['close'] > lowest_low:
                return True
        elif direction == "Bearish":
            # بررسی Sweep در سقف‌ها (Buy Stops)
            highest_high = prev_highs.max()
            if last_candle['high'] > highest_high and last_candle['close'] < highest_high:
                return True
        return False

    def check_m15_confirmation(self, df_m15, direction):
        if df_m15 is None or len(df_m15) < 5: return False
            
        last_candle = df_m15.iloc[-1]
        prev_candle = df_m15.iloc[-2]
        vol_ma = df_m15['volume'].rolling(window=15).mean().iloc[-1]
        
        if pd.isna(vol_ma): return False
            
        # بررسی کندل ورود با حجم بالاتر از ۱.۲ میانگین
        is_volume_confirmed = last_candle['volume'] >= (vol_ma * settings.VOLUME_MULTIPLIER_ENTRY)
        
        if direction == "Bullish":
            is_engulfing = last_candle['close'] > prev_candle['open'] and last_candle['close'] > last_candle['open']
            return is_engulfing and is_volume_confirmed
        else:
            is_engulfing = last_candle['close'] < prev_candle['open'] and last_candle['close'] < last_candle['open']
            return is_engulfing and is_volume_confirmed