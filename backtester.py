import pandas as pd
from settings import settings
from data_fetcher import DataFetcher
from market_structure import MarketStructureAnalyzer
from zone_detector import ZoneDetector
from liquidity_filter import LiquidityAndConfirmationFilter

class SMCBacktester:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.analyzer = MarketStructureAnalyzer()
        self.detector = ZoneDetector()
        self.filter = LiquidityAndConfirmationFilter()
        
    def run_backtest(self, symbols, limit=1000):
        print(f"🛠 در حال اجرای بک‌تست دیباگر روی {len(symbols)} نماد...")
        results = []
        for symbol in symbols:
            df_h4 = self.fetcher.get_candles(symbol, settings.TIMEFRAME_STRUCTURE, limit=limit)
            if df_h4 is None or len(df_h4) < 100: continue
                
            bullish_obs, bearish_obs = self.detector.find_order_blocks(df_h4)
            wins = 0; losses = 0
            trade_logs = []
            
            # بررسی اوردربلاک‌های صعودی
            for ob in bullish_obs:
                entry = ob['top']; sl = ob['bottom']; tp = entry + ((entry - sl) * 2)
                sl_dist_pct = abs(entry - sl) / entry * 100
                lev = max(1, min(50, int(15 / sl_dist_pct))) if sl_dist_pct > 0 else 1
                
                log_item = {
                    "time": str(ob['timestamp']), "type": "Bullish",
                    "zone": f"ورود: ${entry:.4f} | حد ضرر: ${sl:.4f} | هدف: ${tp:.4f} | لوریج: {lev}x",
                    "status": "Skipped", "reason": ""
                }
                
                ob_index = df_h4.index.get_loc(ob['timestamp'])
                df_future = df_h4.iloc[ob_index + 3:] 
                
                entry_candle_idx = None
                for idx, candle in df_future.iterrows():
                    if candle['low'] <= entry:
                        entry_candle_idx = idx
                        break
                
                if entry_candle_idx is None:
                    log_item["reason"] = "قیمت هرگز به نقطه ورود نرسید."
                    trade_logs.append(log_item)
                    continue
                    
                df_before_entry = df_h4.loc[ob['timestamp']:entry_candle_idx]
                if not self.analyzer.check_inducement(df_before_entry, ob['timestamp'], "Bullish"):
                    log_item["reason"] = "رد شد: فاقد تله القا (Inducement)."
                    trade_logs.append(log_item)
                    continue
                    
                df_after_entry = df_h4.loc[entry_candle_idx:]
                for idx, candle in df_after_entry.iterrows():
                    # اول چک کردن استاپ لاس (محافظه‌کارانه)
                    if candle['low'] < sl:
                        losses += 1; log_item["status"] = "Loss"; log_item["reason"] = f"❌ استاپ‌لاس در ${sl:.4f} تاچ شد."
                        break
                    # سپس چک کردن تارگت
                    if candle['high'] >= tp:
                        wins += 1; log_item["status"] = "Win"; log_item["reason"] = f"✅ تارگت سود در ${tp:.4f} تاچ شد."
                        break
                trade_logs.append(log_item)

            # بررسی اوردربلاک‌های نزولی
            for ob in bearish_obs:
                entry = ob['bottom']; sl = ob['top']; tp = entry - ((sl - entry) * 2)
                sl_dist_pct = abs(entry - sl) / entry * 100
                lev = max(1, min(50, int(15 / sl_dist_pct))) if sl_dist_pct > 0 else 1
                
                log_item = {
                    "time": str(ob['timestamp']), "type": "Bearish",
                    "zone": f"ورود: ${entry:.4f} | حد ضرر: ${sl:.4f} | هدف: ${tp:.4f} | لوریج: {lev}x",
                    "status": "Skipped", "reason": ""
                }
                
                ob_index = df_h4.index.get_loc(ob['timestamp'])
                df_future = df_h4.iloc[ob_index + 3:] 
                
                entry_candle_idx = None
                for idx, candle in df_future.iterrows():
                    if candle['high'] >= entry:
                        entry_candle_idx = idx
                        break
                
                if entry_candle_idx is None:
                    log_item["reason"] = "قیمت هرگز به نقطه ورود نرسید."
                    trade_logs.append(log_item)
                    continue
                    
                df_before_entry = df_h4.loc[ob['timestamp']:entry_candle_idx]
                if not self.analyzer.check_inducement(df_before_entry, ob['timestamp'], "Bearish"):
                    log_item["reason"] = "رد شد: فاقد تله القا (Inducement)."
                    trade_logs.append(log_item)
                    continue
                    
                df_after_entry = df_h4.loc[entry_candle_idx:]
                for idx, candle in df_after_entry.iterrows():
                    if candle['high'] > sl:
                        losses += 1; log_item["status"] = "Loss"; log_item["reason"] = f"❌ استاپ‌لاس در ${sl:.4f} تاچ شد."
                        break
                    if candle['low'] <= tp:
                        wins += 1; log_item["status"] = "Win"; log_item["reason"] = f"✅ تارگت سود در ${tp:.4f} تاچ شد."
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