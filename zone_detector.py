import pandas as pd
from settings import settings

class ZoneDetector:
    def check_premium_discount(self, entry_price, main_leg, direction):
        """
        آموزش کد: این تابع لگ اصلی بازار را می‌گیرد و وسط آن را (نقطه ۵۰٪) محاسبه می‌کند.
        برای خرید، قیمت باید در نیمه پایین (Discount) و برای فروش در نیمه بالا (Premium) باشد.
        """
        if main_leg["start"] is None or main_leg["end"] is None:
            return False
            
        equilibrium_50 = (main_leg["start"] + main_leg["end"]) / 2.0
        
        if direction == "Bullish":
            return entry_price <= equilibrium_50
        elif direction == "Bearish":
            return entry_price >= equilibrium_50
        return False

    def is_mitigated(self, df, start_idx, ob_top, ob_bottom, direction):
        """
        آموزش کد: بررسی بکر بودن ناحیه.
        ما بررسی را از 3 کندل بعد (start_idx + 3) آغاز می‌کنیم. 
        چرا؟ چون کندل 1 خود OB است، کندل 2 کندل حرکت اصلی است (که معمولاً به OB چسبیده) 
        و کندل 3 تاییدکننده FVG است. بازگشت به ناحیه (Mitigation) فقط بعد از این فاز معنا دارد.
        """
        # اگر تعداد کندل‌های بعد از OB کمتر از 3 تا باشد، یعنی هنوز بکر است
        if start_idx + 3 >= len(df):
            return False
            
        for i in range(start_idx + 3, len(df)):
            if direction == "Bullish":
                # در لگ صعودی: آیا کف کندل‌های آینده به سقف اوردربلاک ما برخورد کرده است؟
                if df['low'].iloc[i] <= ob_top:
                    return True
            else:
                # در لگ نزولی: آیا سقف کندل‌های آینده به کف اوردربلاک ما برخورد کرده است؟
                if df['high'].iloc[i] >= ob_bottom:
                    return True
                    
        return False

    def find_order_blocks(self, df_h4):
        """
        پیدا کردن اوردربلاک‌های معتبر با شروط هانت، FVG و قانون شدو.
        """
        df = df_h4.copy()
        df['vol_ma20'] = df['volume'].rolling(window=20).mean()
        
        bullish_obs = []
        bearish_obs = []
        
        for i in range(5, len(df) - 2):
            avg_vol = df['vol_ma20'].iloc[i]
            if pd.isna(avg_vol): continue
                
            is_volume_spike = df['volume'].iloc[i+1] >= (avg_vol * settings.VOLUME_MULTIPLIER_IMPULSE)
            
            # --- Bullish OB ---
            if df['close'].iloc[i] < df['open'].iloc[i] and df['close'].iloc[i+1] > df['open'].iloc[i+1]:
                has_fvg = df['low'].iloc[i+2] > df['high'].iloc[i]
                swept_liquidity = df['low'].iloc[i] < df['low'].iloc[i-5:i].min()
                
                if is_volume_spike and has_fvg and swept_liquidity:
                    body_size = df['open'].iloc[i] - df['close'].iloc[i]
                    lower_wick = df['close'].iloc[i] - df['low'].iloc[i]
                    
                    entry_top = df['close'].iloc[i] if lower_wick > body_size else df['high'].iloc[i]
                    entry_bottom = df['low'].iloc[i]
                    note = "Wick OB" if lower_wick > body_size else "Standard OB"
                    
                    # اضافه شدن بررسی Mitigated
                    mitigated = self.is_mitigated(df, i, entry_top, entry_bottom, "Bullish")
                        
                    bullish_obs.append({
                        'top': entry_top, 'bottom': entry_bottom, 
                        'is_mitigated': mitigated,
                        'type': 'Bullish', 'note': note, 'timestamp': df.index[i]
                    })
                    
            # --- Bearish OB ---
            elif df['close'].iloc[i] > df['open'].iloc[i] and df['close'].iloc[i+1] < df['open'].iloc[i+1]:
                has_fvg = df['high'].iloc[i+2] < df['low'].iloc[i]
                swept_liquidity = df['high'].iloc[i] > df['high'].iloc[i-5:i].max()
                
                if is_volume_spike and has_fvg and swept_liquidity:
                    body_size = df['close'].iloc[i] - df['open'].iloc[i]
                    upper_wick = df['high'].iloc[i] - df['close'].iloc[i]
                    
                    entry_top = df['high'].iloc[i]
                    entry_bottom = df['close'].iloc[i] if upper_wick > body_size else df['low'].iloc[i]
                    note = "Wick OB" if upper_wick > body_size else "Standard OB"
                    
                    # اضافه شدن بررسی Mitigated
                    mitigated = self.is_mitigated(df, i, entry_top, entry_bottom, "Bearish")
                        
                    bearish_obs.append({
                        'top': entry_top, 'bottom': entry_bottom, 
                        'is_mitigated': mitigated,
                        'type': 'Bearish', 'note': note, 'timestamp': df.index[i]
                    })
                    
        return bullish_obs, bearish_obs

    def calculate_ote_levels(self, main_leg):
        if main_leg["start"] is None or main_leg["end"] is None:
            return None, None
        diff = abs(main_leg["end"] - main_leg["start"])
        if main_leg["direction"] == "Bullish":
            return main_leg["end"] - (diff * settings.FIB_OTE_HIGH), main_leg["end"] - (diff * settings.FIB_OTE_LOW)
        else:
            return main_leg["end"] + (diff * settings.FIB_OTE_LOW), main_leg["end"] + (diff * settings.FIB_OTE_HIGH)