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
        
    def run_backtest(self, symbols, limit=1000):
        print(f"🛠 در حال اجرای بک‌تست هوشمند دوگانه (H4 + M15) روی {len(symbols)} نماد...")
        results = []
        
        for symbol in symbols:
            df_h4 = self.fetcher.get_candles(symbol, settings.TIMEFRAME_STRUCTURE, limit=limit)
            df_m15 = self.fetcher.get_candles(symbol, settings.TIMEFRAME_ENTRY, limit=limit * 4) 
            
            if df_h4 is None or df_m15 is None or len(df_h4) < 100:
                continue
                
            h4_history = self.analyzer.extract_historical_legs(df_h4)
            bullish_obs, bearish_obs = self.detector.find_order_blocks(df_h4)
            
            wins = 0; losses = 0
            trade_logs = []
            
            # ================= بررسی اوردربلاک‌های صعودی H4 =================
            for ob in bullish_obs:
                ob_time = ob['timestamp']
                
                # بررسی تله نقدینگی (SMT)
                past_events = [e for e in h4_history if pd.to_datetime(e['time']) < ob_time]
                unhunted_bos_liquidity = False
                
                for event in reversed(past_events):
                    if event['type'] == 'CHoCH': break 
                    if event['direction'] == 'Bearish' and event['type'] == 'BOS':
                        bos_low = float(event['break_price'])
                        if ob['bottom'] > bos_low:
                            unhunted_bos_liquidity = True
                            break
                            
                if unhunted_bos_liquidity:
                    trade_logs.append({
                        "time": str(ob_time), "type": "Bullish", "zone": f"${ob['bottom']} - ${ob['top']}",
                        "status": "Skipped", "reason": "⚠️ SMT: اوردربلاک درون نقدینگی هانت‌نشده گیر افتاده است!"
                    })
                    continue

                log_item = {
                    "time": str(ob_time), "type": "Bullish (M15 Confirm)", 
                    "zone": f"ناحیه H4: ${ob['bottom']} - ${ob['top']}",
                    "status": "Skipped", "reason": ""
                }
                
                df_m15_future = df_m15.loc[ob_time:]
                touch_idx = None
                
                # پیدا کردن زمان اولین برخورد به ناحیه H4
                for idx, candle in df_m15_future.iterrows():
                    if candle['low'] <= ob['top']:
                        touch_idx = idx
                        break
                        
                if touch_idx is None:
                    log_item["reason"] = "قیمت هرگز به ناحیه H4 نرسید."
                    trade_logs.append(log_item)
                    continue
                    
                # 🚀 راه‌حل جدید: تاییدیه واقعی M15
                df_m15_after_touch = df_m15_future.loc[touch_idx:]
                m15_choch_idx = None
                entry_price = None
                sl_price = None
                
                # پیدا کردن سقف معتبر قبل از برخورد (مقاومت واقعی M15)
                df_m15_before_touch = df_m15.loc[:touch_idx].tail(15)
                valid_m15_resistance = df_m15_before_touch['high'].max()
                
                for idx, candle in df_m15_after_touch.iloc[1:40].iterrows(): 
                    # اگر قیمت مقاومت واقعی را پرقدرت شکست (CHoCH معتبر)
                    if candle['close'] > valid_m15_resistance:
                        m15_choch_idx = idx
                        entry_price = candle['close']
                        
                        # پیدا کردن پایین‌ترین کف از زمان برخورد
                        absolute_low = df_m15_after_touch.loc[:idx]['low'].min()
                        
                        # 🛡️ سپر محافظتی: 0.2% فاصله از کف برای فرار از نویز و هانت شدن
                        buffer = absolute_low * 0.002 
                        sl_price = absolute_low - buffer
                        break
                    
                if m15_choch_idx is None:
                    log_item["reason"] = "❌ قیمت ناحیه را شکست اما تاییدیه CHoCH نداد (فیلتر شد)."
                    trade_logs.append(log_item)
                    continue

                # تارگت 1:2 (متعادل و منطقی برای افزایش وین‌ریت)
                tp_price = entry_price + ((entry_price - sl_price) * 2.0)
                
                df_trade = df_m15_after_touch.loc[m15_choch_idx:]
                for idx, candle in df_trade.iterrows():
                    if candle['low'] < sl_price:
                        losses += 1
                        log_item["status"] = "Loss"
                        log_item["reason"] = f"❌ استاپ‌لاس در ${sl_price:.2f} تاچ شد."
                        break
                    if candle['high'] >= tp_price:
                        wins += 1
                        log_item["status"] = "Win"
                        log_item["reason"] = f"✅ تارگت سود در ${tp_price:.2f} تاچ شد!"
                        break
                        
                trade_logs.append(log_item)

            # ================= بررسی اوردربلاک‌های نزولی H4 =================
            for ob in bearish_obs:
                ob_time = ob['timestamp']
                
                # بررسی تله نقدینگی (SMT)
                past_events = [e for e in h4_history if pd.to_datetime(e['time']) < ob_time]
                unhunted_bos_liquidity = False
                
                for event in reversed(past_events):
                    if event['type'] == 'CHoCH': break 
                    if event['direction'] == 'Bullish' and event['type'] == 'BOS':
                        bos_high = float(event['break_price'])
                        if ob['top'] < bos_high:
                            unhunted_bos_liquidity = True
                            break
                            
                if unhunted_bos_liquidity:
                    trade_logs.append({
                        "time": str(ob_time), "type": "Bearish", "zone": f"${ob['bottom']} - ${ob['top']}",
                        "status": "Skipped", "reason": "⚠️ SMT: اوردربلاک درون نقدینگی هانت‌نشده گیر افتاده است!"
                    })
                    continue

                log_item = {
                    "time": str(ob_time), "type": "Bearish (M15 Confirm)", 
                    "zone": f"ناحیه H4: ${ob['bottom']} - ${ob['top']}",
                    "status": "Skipped", "reason": ""
                }
                
                df_m15_future = df_m15.loc[ob_time:]
                touch_idx = None
                
                for idx, candle in df_m15_future.iterrows():
                    if candle['high'] >= ob['bottom']:
                        touch_idx = idx
                        break
                        
                if touch_idx is None:
                    log_item["reason"] = "قیمت هرگز به ناحیه H4 نرسید."
                    trade_logs.append(log_item)
                    continue
                    
                df_m15_after_touch = df_m15_future.loc[touch_idx:]
                m15_choch_idx = None
                entry_price = None
                sl_price = None
                
                # پیدا کردن کف معتبر قبل از برخورد (حمایت واقعی M15)
                df_m15_before_touch = df_m15.loc[:touch_idx].tail(15)
                valid_m15_support = df_m15_before_touch['low'].min()
                
                for idx, candle in df_m15_after_touch.iloc[1:40].iterrows(): 
                    # شکست حمایت پرقدرت رو به پایین
                    if candle['close'] < valid_m15_support:
                        m15_choch_idx = idx
                        entry_price = candle['close']
                        
                        absolute_high = df_m15_after_touch.loc[:idx]['high'].max()
                        
                        # 🛡️ سپر محافظتی بالا
                        buffer = absolute_high * 0.002 
                        sl_price = absolute_high + buffer
                        break
                    
                if m15_choch_idx is None:
                    log_item["reason"] = "❌ قیمت ناحیه را شکست اما تاییدیه CHoCH نداد (فیلتر شد)."
                    trade_logs.append(log_item)
                    continue

                tp_price = entry_price - ((sl_price - entry_price) * 2.0)
                
                df_trade = df_m15_after_touch.loc[m15_choch_idx:]
                for idx, candle in df_trade.iterrows():
                    if candle['high'] > sl_price:
                        losses += 1
                        log_item["status"] = "Loss"
                        log_item["reason"] = f"❌ استاپ‌لاس در ${sl_price:.2f} تاچ شد."
                        break
                    if candle['low'] <= tp_price:
                        wins += 1
                        log_item["status"] = "Win"
                        log_item["reason"] = f"✅ تارگت سود در ${tp_price:.2f} تاچ شد!"
                        break
                        
                trade_logs.append(log_item)

            trade_logs.sort(key=lambda x: x['time'], reverse=True)
            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            results.append({
                "symbol": symbol, "wins": wins, "losses": losses, "win_rate": win_rate,
                "total_found": len(bullish_obs) + len(bearish_obs), "trade_logs": trade_logs
            })
            
        return results