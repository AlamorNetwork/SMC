import pandas as pd
from settings import settings

class ZoneDetector:
    def find_order_blocks(self, df_h4):
        """
        پیدا کردن اوردر بلاک‌های صعودی و نزولی (OB) با تایید حجم بالای ۱.۵ برابر میانگین
        """
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
                    'top': df['high'].iloc[i], 
                    'bottom': df['low'].iloc[i], 
                    'type': 'Bullish',
                    'timestamp': df.index[i]  # <-- این خط اضافه شد
                })
            # پیدا کردن Bearish OB
            elif df['close'].iloc[i] > df['open'].iloc[i] and df['close'].iloc[i+1] < df['open'].iloc[i+1] and is_volume_spike:
                bearish_obs.append({
                    'top': df['high'].iloc[i], 
                    'bottom': df['low'].iloc[i], 
                    'type': 'Bearish',
                    'timestamp': df.index[i]  # <-- این خط اضافه شد
                })
        return bullish_obs, bearish_obs

    def find_fvgs(self, df_h4):
        """
        پیدا کردن گپ‌های ارزش منصفانه (FVG) در تایم‌فریم H4
        """
        fvgs = []
        for i in range(2, len(df_h4)):
            # Bullish FVG
            if df_h4['high'].iloc[i-2] < df_h4['low'].iloc[i]:
                fvgs.append({
                    'type': 'Bullish',
                    'top': df_h4['low'].iloc[i],
                    'bottom': df_h4['high'].iloc[i-2],
                    'timestamp': df_h4.index[i-1]
                })
            # Bearish FVG
            elif df_h4['low'].iloc[i-2] > df_h4['high'].iloc[i]:
                fvgs.append({
                    'type': 'Bearish',
                    'top': df_h4['low'].iloc[i-2],
                    'bottom': df_h4['high'].iloc[i],
                    'timestamp': df_h4.index[i-1]
                })
        return fvgs

    def calculate_ote_levels(self, main_leg):
        """
        محاسبه محدوده طلایی ورود OTE (اصلاح ۷۱٪ تا ۷۹٪ فیبوناچی)
        """
        if main_leg["start"] is None or main_leg["end"] is None:
            return None, None
            
        start = main_leg["start"]
        end = main_leg["end"]
        diff = abs(end - start)
        
        if main_leg["direction"] == "Bullish":
            ote_low = end - (diff * settings.FIB_OTE_HIGH)
            ote_high = end - (diff * settings.FIB_OTE_LOW)
        else:
            ote_low = end + (diff * settings.FIB_OTE_LOW)
            ote_high = end + (diff * settings.FIB_OTE_HIGH)
            
        return ote_low, ote_high