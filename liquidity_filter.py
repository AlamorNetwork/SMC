import pandas as pd
from settings import settings

class LiquidityAndConfirmationFilter:
    def check_cbs_entry(self, df_h4, direction):
        """
        آموزش کد: استراتژی CBS (Candle Breakout Strategy).
        این متد بررسی می‌کند آیا آخرین کندل در همان تایم فریم اصلی (H4) نقدینگی را هانت کرده 
        و سریعاً کندل بعدی آن را پوشش (Engulf) داده است تا مستقیماً وارد شویم.
        """
        if len(df_h4) < 5: return False
            
        last_candle = df_h4.iloc[-1]
        prev_highs = df_h4['high'].iloc[:-2]
        prev_lows = df_h4['low'].iloc[:-2]
        
        if direction == "Bullish":
            lowest_low = prev_lows.min()
            # شرط هانت و بسته شدن بالای کف قبلی (ردجکشن)
            if last_candle['low'] < lowest_low and last_candle['close'] > lowest_low:
                # شرط تایید حجم بالا برای ورود CBS
                vol_ma = df_h4['volume'].rolling(window=20).mean().iloc[-1]
                if last_candle['volume'] >= (vol_ma * settings.VOLUME_MULTIPLIER_ENTRY):
                    return True
                    
        elif direction == "Bearish":
            highest_high = prev_highs.max()
            if last_candle['high'] > highest_high and last_candle['close'] < highest_high:
                vol_ma = df_h4['volume'].rolling(window=20).mean().iloc[-1]
                if last_candle['volume'] >= (vol_ma * settings.VOLUME_MULTIPLIER_ENTRY):
                    return True
                    
        return False

    def check_choch_entry(self, df_m15, direction):
        """
        آموزش کد: تاییدیه کلاسیک در تایم فریم پایین‌تر (M15).
        بعد از برخورد به ناحیه H4، منتظر کندل پوشا و تغییر ماهیت در ۱۵ دقیقه‌ای می‌مانیم.
        """
        if df_m15 is None or len(df_m15) < 5: return False
            
        last_candle = df_m15.iloc[-1]
        prev_candle = df_m15.iloc[-2]
        vol_ma = df_m15['volume'].rolling(window=15).mean().iloc[-1]
        
        if pd.isna(vol_ma): return False
            
        is_volume_confirmed = last_candle['volume'] >= (vol_ma * settings.VOLUME_MULTIPLIER_ENTRY)
        
        if direction == "Bullish":
            # کندل سبز باید کندل قرمز قبلی را پوشش دهد
            is_engulfing = last_candle['close'] > prev_candle['open'] and last_candle['close'] > last_candle['open']
            return is_engulfing and is_volume_confirmed
        else:
            # کندل قرمز باید کندل سبز قبلی را پوشش دهد
            is_engulfing = last_candle['close'] < prev_candle['open'] and last_candle['close'] < last_candle['open']
            return is_engulfing and is_volume_confirmed