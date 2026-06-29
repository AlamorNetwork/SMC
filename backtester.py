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
            
            if df_h4 is None or len(df_h4) < 100:
                continue
                
            bullish_obs, bearish_obs = self.detector.find_order_blocks(df_h4)
            wins = 0
            losses = 0
            trade_logs = [] # 👈 ذخیره لاگ و جزئیات تک‌تک اوردربلاک‌ها
            
            # ================= بررسی اوردربلاک‌های صعودی =================
            for ob in bullish_obs:
                log_item = {
                    "time": str(ob['timestamp']),
                    "type": "Bullish",
                    "zone": f"${ob['bottom']:.2f} - ${ob['top']:.2f}",
                    "status": "Skipped",
                    "reason": ""
                }
                
                ob_index = df_h4.index.get_loc(ob['timestamp'])
                df_future = df_h4.iloc[ob_index + 3:] 
                
                entry_candle_idx = None
                for idx, candle in df_future.iterrows():
                    if candle['low'] <= ob['top']:
                        entry_candle_idx = idx
                        break
                
                if entry_candle_idx is None:
                    log_item["reason"] = "قیمت هرگز برای ورود (Mitigation) به ناحیه برنگشت."
                    trade_logs.append(log_item)
                    continue
                    
                df_before_entry = df_h4.loc[ob['timestamp']:entry_candle_idx]
                if not self.analyzer.check_inducement(df_before_entry, ob['timestamp'], "Bullish"):
                    log_item["reason"] = "رد شد: فاقد تله نقدینگی (Inducement) قبل از ورود."
                    trade_logs.append(log_item)
                    continue
                    
                df_after_entry = df_h4.loc[entry_candle_idx:]
                risk = ob['top'] - ob['bottom']
                target = ob['top'] + (risk * 2)
                
                for idx, candle in df_after_entry.iterrows():
                    if candle['low'] < ob['bottom']:
                        losses += 1
                        log_item["status"] = "Loss"
                        log_item["reason"] = "❌ استاپ‌لاس خورد (حد ضرر فعال شد)."
                        break
                    if candle['high'] >= target:
                        wins += 1
                        log_item["status"] = "Win"
                        log_item["reason"] = "✅ معامله با موفقیت به تارگت (TP) رسید."
                        break
                        
                trade_logs.append(log_item)

            # ================= بررسی اوردربلاک‌های نزولی =================
            for ob in bearish_obs:
                log_item = {
                    "time": str(ob['timestamp']),
                    "type": "Bearish",
                    "zone": f"${ob['bottom']:.2f} - ${ob['top']:.2f}",
                    "status": "Skipped",
                    "reason": ""
                }
                
                ob_index = df_h4.index.get_loc(ob['timestamp'])
                df_future = df_h4.iloc[ob_index + 3:] 
                
                entry_candle_idx = None
                for idx, candle in df_future.iterrows():
                    if candle['high'] >= ob['bottom']:
                        entry_candle_idx = idx
                        break
                
                if entry_candle_idx is None:
                    log_item["reason"] = "قیمت هرگز برای ورود به ناحیه برنگشت."
                    trade_logs.append(log_item)
                    continue
                    
                df_before_entry = df_h4.loc[ob['timestamp']:entry_candle_idx]
                if not self.analyzer.check_inducement(df_before_entry, ob['timestamp'], "Bearish"):
                    log_item["reason"] = "رد شد: فاقد تله نقدینگی (Inducement)."
                    trade_logs.append(log_item)
                    continue
                    
                df_after_entry = df_h4.loc[entry_candle_idx:]
                risk = ob['top'] - ob['bottom']
                target = ob['bottom'] - (risk * 2)
                
                for idx, candle in df_after_entry.iterrows():
                    if candle['high'] > ob['top']:
                        losses += 1
                        log_item["status"] = "Loss"
                        log_item["reason"] = "❌ استاپ‌لاس خورد."
                        break
                    if candle['low'] <= target:
                        wins += 1
                        log_item["status"] = "Win"
                        log_item["reason"] = "✅ معامله با موفقیت به تارگت رسید."
                        break
                        
                trade_logs.append(log_item)

            # مرتب‌سازی لاگ‌ها بر اساس زمان (از جدیدترین به قدیمی‌ترین)
            trade_logs.sort(key=lambda x: x['time'], reverse=True)

            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            results.append({
                "symbol": symbol,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "total_found": len(bullish_obs) + len(bearish_obs),
                "trade_logs": trade_logs # ارسال لاگ‌ها به فرانت‌اند
            })

        return results