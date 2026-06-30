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

    def find_order_blocks(self, df_h4):
        """
        تشخیص اوردربلاک با قابلیت درک هانت شدن BOS و نقدینگی‌های ماکرو.
        """
        df = df_h4.copy()
        
        # ۱. ابتدا ساختار واقعی و BOSها را روی چارت مپ می‌کنیم
        from market_structure import MarketStructureAnalyzer
        msa = MarketStructureAnalyzer()
        df = msa.map_true_structure(df)
        
        df['vol_ma20'] = df['volume'].rolling(window=20).mean()
        
        bullish_obs = []
        bearish_obs = []
        
        # استخراج تایم‌فریم و مقادیر کف و سقف‌های ماژور (همان‌هایی که BOS می‌سازند)
        macro_lows = df[df['macro_low'].notna()]['macro_low']
        macro_highs = df[df['macro_high'].notna()]['macro_high']
        
        for i in range(5, len(df) - 2):
            avg_vol = df['vol_ma20'].iloc[i]
            if pd.isna(avg_vol): continue
                
            is_volume_spike = df['volume'].iloc[i+1] >= (avg_vol * settings.VOLUME_MULTIPLIER_IMPULSE)
            
            # استخراج آخرین سقف و کف مهمِ قبل از زمانِ تشکیل این اوردربلاک
            last_macro_low = macro_lows.loc[:df.index[i]].iloc[-1] if not macro_lows.loc[:df.index[i]].empty else None
            last_macro_high = macro_highs.loc[:df.index[i]].iloc[-1] if not macro_highs.loc[:df.index[i]].empty else None
            
            # ================= Bullish OB =================
            if df['close'].iloc[i] < df['open'].iloc[i] and df['close'].iloc[i+1] > df['open'].iloc[i+1]:
                has_fvg = df['low'].iloc[i+2] > df['high'].iloc[i]
                
                if is_volume_spike and has_fvg:
                    ob_low = df['low'].iloc[i]
                    
                    is_macro_sweep = False
                    is_smt = False
                    liq_status = "ناشناخته"
                    
                    # بررسی هانت محلی (حداقل ۵ کندل قبل)
                    local_sweep = ob_low < df['low'].iloc[i-5:i].min()
                    
                    # 🚀 بررسی وضعیت هانت نسبت به BOS و لگ ماکرو
                    if last_macro_low is not None:
                        # حالت طلایی: اوردربلاک دقیقاً کف ماژور قبلی را هانت کرده است (جارو کردن نقدینگی اصلی)
                        if ob_low <= last_macro_low:
                            is_macro_sweep = True
                            liq_status = "⭐ طلایی (هانت کف ماژور)"
                        # حالت خطرناک: اوردربلاک بالاتر از کف ماژور است
                        elif ob_low > last_macro_low:
                            if not local_sweep:
                                is_smt = True # تله پول هوشمند! درون نقدینگی است و هانت نکرده
                            else:
                                liq_status = "⚠️ پرریسک (فقط هانت داخلی)"
                                
                    # اگر تله نقدینگی (SMT) باشد، کلاً نادیده‌اش می‌گیریم و در داشبورد نمی‌آوریم
                    if is_smt:
                        continue
                        
                    # اگر هیچ‌کدام از هانت‌ها را انجام نداده باشد معتبر نیست
                    if not local_sweep and not is_macro_sweep:
                        continue
                        
                    body_size = df['open'].iloc[i] - df['close'].iloc[i]
                    lower_wick = df['close'].iloc[i] - df['low'].iloc[i]
                    entry_top = df['close'].iloc[i] if lower_wick > body_size else df['high'].iloc[i]
                    entry_bottom = ob_low
                    
                    mitigated = self.is_mitigated(df, i, entry_top, entry_bottom, "Bullish")
                    bullish_obs.append({
                        'top': entry_top, 'bottom': entry_bottom, 
                        'is_mitigated': mitigated, 'type': 'Bullish', 'note': liq_status, 'timestamp': df.index[i]
                    })
                    
            # ================= Bearish OB =================
            elif df['close'].iloc[i] > df['open'].iloc[i] and df['close'].iloc[i+1] < df['open'].iloc[i+1]:
                has_fvg = df['high'].iloc[i+2] < df['low'].iloc[i]
                
                if is_volume_spike and has_fvg:
                    ob_high = df['high'].iloc[i]
                    
                    is_macro_sweep = False
                    is_smt = False
                    liq_status = "ناشناخته"
                    
                    local_sweep = ob_high > df['high'].iloc[i-5:i].max()
                    
                    if last_macro_high is not None:
                        if ob_high >= last_macro_high:
                            is_macro_sweep = True
                            liq_status = "⭐ طلایی (هانت سقف ماژور)"
                        elif ob_high < last_macro_high:
                            if not local_sweep:
                                is_smt = True
                            else:
                                liq_status = "⚠️ پرریسک (فقط هانت داخلی)"
                                
                    if is_smt:
                        continue
                        
                    if not local_sweep and not is_macro_sweep:
                        continue
                        
                    body_size = df['close'].iloc[i] - df['open'].iloc[i]
                    upper_wick = df['high'].iloc[i] - df['close'].iloc[i]
                    entry_top = ob_high
                    entry_bottom = df['close'].iloc[i] if upper_wick > body_size else df['low'].iloc[i]
                    
                    mitigated = self.is_mitigated(df, i, entry_top, entry_bottom, "Bearish")
                    bearish_obs.append({
                        'top': entry_top, 'bottom': entry_bottom, 
                        'is_mitigated': mitigated, 'type': 'Bearish', 'note': liq_status, 'timestamp': df.index[i]
                    })
                    
        return bullish_obs, bearish_obs