import pandas as pd
from settings import settings

class ZoneDetector:
    def find_order_blocks(self, df_h4):
        """
        پیدا کردن اوردر بلاک‌های معتبر با شروط سخت‌گیرانه:
        ۱. هانت نقدینگی (Sweep)
        ۲. داشتن FVG بعد از خود
        ۳. تایید حجم
        ۴. قانون شدو (اگر شدو بلندتر از بدنه باشد، محدوده ورود فقط شدو است)
        """
        df = df_h4.copy()
        df['vol_ma20'] = df['volume'].rolling(window=20).mean()
        
        bullish_obs = []
        bearish_obs = []
        
        for i in range(5, len(df) - 2):
            avg_vol = df['vol_ma20'].iloc[i]
            if pd.isna(avg_vol): continue
                
            # شرط حجم حرکت بعدی
            is_volume_spike = df['volume'].iloc[i+1] >= (avg_vol * settings.VOLUME_MULTIPLIER_IMPULSE)
            
            # --- بررسی Bullish OB ---
            # کندل نزولی قبل از حرکت صعودی
            if df['close'].iloc[i] < df['open'].iloc[i] and df['close'].iloc[i+1] > df['open'].iloc[i+1]:
                
                # شرط FVG: آیا بین های کندل فعلی و لوی دو کندل بعد گپ وجود دارد؟
                has_fvg = df['low'].iloc[i+2] > df['high'].iloc[i]
                
                # شرط Sweep (هانت): آیا کف این کندل، کف ۵ کندل قبلی خود را زده است؟
                swept_liquidity = df['low'].iloc[i] < df['low'].iloc[i-5:i].min()
                
                if is_volume_spike and has_fvg and swept_liquidity:
                    body_size = df['open'].iloc[i] - df['close'].iloc[i]
                    lower_wick = df['close'].iloc[i] - df['low'].iloc[i]
                    
                    # قانون شدو (Wick Rule): اگر شدو پایین بزرگتر از بدنه باشد
                    if lower_wick > body_size:
                        entry_top = df['close'].iloc[i]
                        entry_bottom = df['low'].iloc[i]
                        note = "Wick OB (شدو بزرگتر از بدنه)"
                    else:
                        entry_top = df['high'].iloc[i]
                        entry_bottom = df['low'].iloc[i]
                        note = "Standard OB"
                        
                    bullish_obs.append({
                        'top': entry_top, 'bottom': entry_bottom, 
                        'full_high': df['high'].iloc[i], 'full_low': df['low'].iloc[i],
                        'type': 'Bullish', 'note': note, 'timestamp': df.index[i]
                    })
                    
            # --- بررسی Bearish OB ---
            # کندل صعودی قبل از ریزش
            elif df['close'].iloc[i] > df['open'].iloc[i] and df['close'].iloc[i+1] < df['open'].iloc[i+1]:
                
                # شرط FVG
                has_fvg = df['high'].iloc[i+2] < df['low'].iloc[i]
                
                # شرط Sweep (هانت): آیا سقف این کندل، سقف ۵ کندل قبلی را زده است؟
                swept_liquidity = df['high'].iloc[i] > df['high'].iloc[i-5:i].max()
                
                if is_volume_spike and has_fvg and swept_liquidity:
                    body_size = df['close'].iloc[i] - df['open'].iloc[i]
                    upper_wick = df['high'].iloc[i] - df['close'].iloc[i]
                    
                    if upper_wick > body_size:
                        entry_top = df['high'].iloc[i]
                        entry_bottom = df['close'].iloc[i]
                        note = "Wick OB (شدو بزرگتر از بدنه)"
                    else:
                        entry_top = df['high'].iloc[i]
                        entry_bottom = df['low'].iloc[i]
                        note = "Standard OB"
                        
                    bearish_obs.append({
                        'top': entry_top, 'bottom': entry_bottom, 
                        'full_high': df['high'].iloc[i], 'full_low': df['low'].iloc[i],
                        'type': 'Bearish', 'note': note, 'timestamp': df.index[i]
                    })
                    
        return bullish_obs, bearish_obs

    def find_fvgs(self, df_h4):
        fvgs = []
        for i in range(2, len(df_h4)):
            if df_h4['high'].iloc[i-2] < df_h4['low'].iloc[i]:
                fvgs.append({'type': 'Bullish', 'top': df_h4['low'].iloc[i], 'bottom': df_h4['high'].iloc[i-2], 'timestamp': df_h4.index[i-1]})
            elif df_h4['low'].iloc[i-2] > df_h4['high'].iloc[i]:
                fvgs.append({'type': 'Bearish', 'top': df_h4['low'].iloc[i-2], 'bottom': df_h4['high'].iloc[i], 'timestamp': df_h4.index[i-1]})
        return fvgs

    def calculate_ote_levels(self, main_leg):
        if main_leg["start"] is None or main_leg["end"] is None:
            return None, None
        start, end = main_leg["start"], main_leg["end"]
        diff = abs(end - start)
        if main_leg["direction"] == "Bullish":
            return end - (diff * settings.FIB_OTE_HIGH), end - (diff * settings.FIB_OTE_LOW)
        else:
            return end + (diff * settings.FIB_OTE_LOW), end + (diff * settings.FIB_OTE_HIGH)

    def refine_ob_in_m15(self, h4_ob, df_m15):
        """
        بهینه‌سازی اوردر بلاک 4H در تایم‌فریم 15M (Refinement)
        وظیفه: پیدا کردن اوردر بلاک‌های کوچک‌تر درون محدوده اوردر بلاک 4 ساعته برای ریسک به ریوارد بهتر
        """
        # فیلتر کردن کندل‌های 15 دقیقه‌ای که از نظر زمانی و قیمتی داخل OB چهار ساعته هستند
        ob_start_time = h4_ob['timestamp']
        m15_in_zone = df_m15.loc[ob_start_time:]
        
        refined_zone = None
        # در اینجا منطق پیدا کردن آخرین کندل مخالف در M15 پیاده‌سازی می‌شود
        # برای سادگی، فعلاً زون 4H را برمی‌گردانیم اما این متد آماده توسعه برای پنل وب است
        return h4_ob