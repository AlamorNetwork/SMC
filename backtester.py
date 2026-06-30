import pandas as pd
from settings import settings
from data_fetcher import DataFetcher
from market_structure import MarketStructureAnalyzer
from zone_detector import ZoneDetector
import asyncio

class SMCBacktester:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.analyzer = MarketStructureAnalyzer()
        self.detector = ZoneDetector()
        
    def run_backtest(self, symbols, limit=10000):
        print(f"🛠 در حال اجرای بک‌تست دوگانه (H4 + M15) روی {len(symbols)} نماد...")
        results = []
        
        for symbol in symbols:
            # ۱. دریافت دیتای هر دو تایم‌فریم
            print(f"⏳ دریافت دیتای H4 و M15 برای {symbol}...")
            df_h4 = self.fetcher.get_candles(symbol, settings.TIMEFRAME_STRUCTURE, limit=limit)
            # دیتای M15 باید ۴ برابر H4 باشد تا جزئیات را پوشش دهد
            df_m15 = self.fetcher.get_candles(symbol, settings.TIMEFRAME_ENTRY, limit=limit * 4) 
            
            if df_h4 is None or df_m15 is None or len(df_h4) < 100:
                continue
                
            # ۲. استخراج تاریخچه ساختار H4 (برای بررسی هانت BOS ها)
            h4_history = self.analyzer.extract_historical_legs(df_h4)
            bullish_obs, bearish_obs = self.detector.find_order_blocks(df_h4)
            
            wins = 0; losses = 0
            trade_logs = []
            
            print(f"🧱 {len(bullish_obs) + len(bearish_obs)} اوردربلاک H4 یافت شد. در حال زوم روی M15...")

            # ================= بررسی اوردربلاک‌های صعودی H4 =================
            for ob in bullish_obs:
                ob_time = ob['timestamp']
                
                # --- فیلتر هوشمند نقدینگی (بررسی BOS های تاریخی نزولی) ---
                # پیدا کردن تمام BOSهای نزولی قبل از این OB تا زمان CHoCH قبلی
                past_events = [e for e in h4_history if pd.to_datetime(e['time']) < ob_time]
                unhunted_bos_liquidity = False
                
                for event in reversed(past_events):
                    if event['type'] == 'CHoCH': 
                        break # رسیدیم به تغییر روند قبلی، جستجو متوقف می‌شود
                    if event['direction'] == 'Bearish' and event['type'] == 'BOS':
                        # آیا قیمت کف این BOS را هانت کرده است؟
                        bos_low = float(event['break_price'])
                        if ob['bottom'] > bos_low:
                            unhunted_bos_liquidity = True
                            break
                            
                if unhunted_bos_liquidity:
                    trade_logs.append({
                        "time": str(ob_time), "type": "Bullish", "zone": f"${ob['bottom']} - ${ob['top']}",
                        "status": "Skipped", "reason": "⚠️ SMT: اوردربلاک درون نقدینگی BOS نزولی قبلی گیر افتاده و هانت نکرده است!"
                    })
                    continue

                # --- جستجو برای ورود در M15 ---
                log_item = {
                    "time": str(ob_time), "type": "Bullish (M15 Confirm)", 
                    "zone": f"ناحیه H4: ${ob['bottom']} - ${ob['top']}",
                    "status": "Skipped", "reason": ""
                }
                
                # پیدا کردن کندل‌های M15 بعد از تشکیل OB چهار ساعته
                df_m15_future = df_m15.loc[ob_time:]
                
                touch_idx = None
                for idx, candle in df_m15_future.iterrows():
                    # اولین برخورد قیمت M15 به سقف اوردربلاک H4
                    if candle['low'] <= ob['top']:
                        touch_idx = idx
                        break
                        
                if touch_idx is None:
                    log_item["reason"] = "قیمت هرگز به ناحیه H4 نرسید."
                    trade_logs.append(log_item)
                    continue
                    
                # 🚀 پیدا کردن تاییدیه CHoCH در M15 بعد از برخورد
                df_m15_after_touch = df_m15_future.loc[touch_idx:]
                m15_choch_idx = None
                entry_price = None
                sl_price = None
                
                # یک شبیه‌سازی ساده از پیدا کردن CHoCH صعودی M15
                last_m15_high = df_m15_after_touch['high'].iloc[0:5].max()
                for idx, candle in df_m15_after_touch.iloc[5:40].iterrows(): # تا ۴۰ کندل ۱۵ دقیقه صبر می‌کنیم
                    if candle['close'] > last_m15_high: # CHoCH رخ داد!
                        m15_choch_idx = idx
                        entry_price = candle['close'] # ورود محافظه‌کارانه بعد از شکست
                        sl_price = df_m15_after_touch.loc[:idx]['low'].min() # استاپ زیر پایین‌ترین شدوی M15
                        break
                    
                if m15_choch_idx is None:
                    log_item["reason"] = "❌ شکسته شد: قیمت ناحیه H4 را درنوردید و تاییدیه M15 (CHoCH) نداد."
                    trade_logs.append(log_item)
                    continue

                # محاسبه سود و زیان بر اساس استاپ لاس کوچولوی M15 !
                tp_price = entry_price + ((entry_price - sl_price) * 3) # ریوارد 1:3 در M15
                
                # شبیه‌سازی معامله از لحظه ورود M15
                df_trade = df_m15_after_touch.loc[m15_choch_idx:]
                for idx, candle in df_trade.iterrows():
                    if candle['low'] < sl_price:
                        losses += 1; log_item["status"] = "Loss"; log_item["reason"] = f"❌ استاپ‌لاس M15 در ${sl_price:.2f} تاچ شد."
                        break
                    if candle['high'] >= tp_price:
                        wins += 1; log_item["status"] = "Win"; log_item["reason"] = f"✅ تارگت R:3 در ${tp_price:.2f} تاچ شد!"
                        break
                        
                trade_logs.append(log_item)

            # (نکته: بخش Bearish OB هم دقیقاً با همین منطق معکوس تکرار می‌شود - برای کوتاه شدن کد در اینجا فقط لاجیک Bullish را نوشتم تا تست کنی. در صورت موفقیت Bearish را هم اضافه می‌کنیم).

            trade_logs.sort(key=lambda x: x['time'], reverse=True)
            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            results.append({
                "symbol": symbol, "wins": wins, "losses": losses, "win_rate": win_rate,
                "total_found": len(bullish_obs), "trade_logs": trade_logs
            })
            
        return results