import pandas as pd
from settings import settings

class ZoneDetector:
    def find_order_blocks(self, df_h4):
        df = df_h4.copy()
        df['vol_ma20'] = df['volume'].rolling(window=20).mean()
        
        bullish_obs = []
        bearish_obs = []
        
        for i in range(2, len(df) - 1):
            avg_vol = df['vol_ma20'].iloc[i]
            if pd.isna(avg_vol): continue
                
            is_volume_spike = df['volume'].iloc[i+1] >= (avg_vol * settings.VOLUME_MULTIPLIER_IMPULSE)
            
            # پیدا کردن Bullish OB
            if df['close'].iloc[i] < df['open'].iloc[i] and df['close'].iloc[i+1] > df['open'].iloc[i+1] and is_volume_spike:
                bullish_obs.append({
                    'top': df['high'].iloc[i], 'bottom': df['low'].iloc[i], 'type': 'Bullish'
                })
            # پیدا کردن Bearish OB
            elif df['close'].iloc[i] > df['open'].iloc[i] and df['close'].iloc[i+1] < df['open'].iloc[i+1] and is_volume_spike:
                bearish_obs.append({
                    'top': df['high'].iloc[i], 'bottom': df['low'].iloc[i], 'type': 'Bearish'
                })
        return bullish_obs, bearish_obs

    def calculate_ote_levels(self, main_leg):
        if main_leg["start"] is None or main_leg["end"] is None:
            return None, None
            
        start, end = main_leg["start"], main_leg["end"]
        diff = abs(end - start)
        
        if main_leg["direction"] == "Bullish":
            ote_low = end - (diff * settings.FIB_OTE_HIGH)
            ote_high = end - (diff * settings.FIB_OTE_LOW)
        else:
            ote_low = end + (diff * settings.FIB_OTE_LOW)
            ote_high = end + (diff * settings.FIB_OTE_HIGH)
            
        return ote_low, ote_high