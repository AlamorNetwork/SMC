import pandas as pd
from settings import settings

class ZoneDetector:
    def check_premium_discount(self, entry_price, main_leg, direction):
        if main_leg["start"] is None or main_leg["end"] is None:
            return False
            
        equilibrium_50 = (main_leg["start"] + main_leg["end"]) / 2.0
        
        if direction == "Bullish":
            return entry_price <= equilibrium_50
        elif direction == "Bearish":
            return entry_price >= equilibrium_50
        return False

    def is_mitigated(self, df, start_idx, ob_top, ob_bottom, direction):
        if start_idx + 3 >= len(df):
            return False
            
        for i in range(start_idx + 3, len(df)):
            if direction == "Bullish":
                if df['low'].iloc[i] <= ob_top:
                    return True
            else:
                if df['high'].iloc[i] >= ob_bottom:
                    return True
        return False

    def is_smart_money_trap(self, df, ob_timestamp, ob_type, last_macro_low, last_macro_high):
        """
        این تابع بررسی می‌کند که آیا اوردربلاک درون نقدینگی‌های ماژور قرار دارد یا خیر.
        """
        try:
            ob_index = df.index.get_loc(ob_timestamp)
            ob_row = df.iloc[ob_index]
            
            if ob_type == "Bullish" and last_macro_low is not None:
                # اگر اوردربلاک بالاتر از نقدینگی اصلی شکل گرفته، تله است
                if ob_row['low'] > last_macro_low:
                    return True 
                    
            elif ob_type == "Bearish" and last_macro_high is not None:
                if ob_row['high'] < last_macro_high:
                    return True 
        except:
            pass
            
        return False

    def find_order_blocks(self, df_h4, last_macro_low=None, last_macro_high=None):
        df = df_h4.copy()
        df['vol_ma20'] = df['volume'].rolling(window=20).mean()
        
        bullish_obs = []
        bearish_obs = []
        
        # در صورتی که ساختار ماژور پاس داده نشده بود، به صورت خودکار محاسبه شود
        if last_macro_low is None or last_macro_high is None:
            from market_structure import MarketStructureAnalyzer
            _, temp_leg, _ = MarketStructureAnalyzer().analyze_structure(df_h4)
            last_macro_low = temp_leg.get("last_macro_low")
            last_macro_high = temp_leg.get("last_macro_high")
        
        for i in range(5, len(df) - 2):
            avg_vol = df['vol_ma20'].iloc[i]
            if pd.isna(avg_vol): continue
                
            is_volume_spike = df['volume'].iloc[i+1] >= (avg_vol * settings.VOLUME_MULTIPLIER_IMPULSE)
            
            # --- Bullish OB ---
            if df['close'].iloc[i] < df['open'].iloc[i] and df['close'].iloc[i+1] > df['open'].iloc[i+1]:
                has_fvg = df['low'].iloc[i+2] > df['high'].iloc[i]
                swept_liquidity = df['low'].iloc[i] < df['low'].iloc[i-5:i].min() # حفظ هانت محلی ساختار
                
                if is_volume_spike and has_fvg and swept_liquidity:
                    body_size = df['open'].iloc[i] - df['close'].iloc[i]
                    lower_wick = df['close'].iloc[i] - df['low'].iloc[i]
                    
                    entry_top = df['close'].iloc[i] if lower_wick > body_size else df['high'].iloc[i]
                    entry_bottom = df['low'].iloc[i]
                    note = "Wick OB" if lower_wick > body_size else "Standard OB"
                    ob_timestamp = df.index[i]
                    
                    # 🚀 اضافه شدن فیلتر هوشمند تله نقدینگی (SMT)
                    if self.is_smart_money_trap(df, ob_timestamp, "Bullish", last_macro_low, last_macro_high):
                        continue
                    
                    mitigated = self.is_mitigated(df, i, entry_top, entry_bottom, "Bullish")
                        
                    bullish_obs.append({
                        'top': entry_top, 'bottom': entry_bottom, 
                        'is_mitigated': mitigated, 'type': 'Bullish', 'note': note, 'timestamp': ob_timestamp
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
                    ob_timestamp = df.index[i]
                    
                    # 🚀 اضافه شدن فیلتر هوشمند تله نقدینگی (SMT)
                    if self.is_smart_money_trap(df, ob_timestamp, "Bearish", last_macro_low, last_macro_high):
                        continue
                    
                    mitigated = self.is_mitigated(df, i, entry_top, entry_bottom, "Bearish")
                        
                    bearish_obs.append({
                        'top': entry_top, 'bottom': entry_bottom, 
                        'is_mitigated': mitigated, 'type': 'Bearish', 'note': note, 'timestamp': ob_timestamp
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