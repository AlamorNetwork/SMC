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
        
    def run_backtest(self, symbols, limit=500):
        print(f"🛠 در حال شروع بک‌تست پیشرفته روی {len(symbols)} نماد با {limit} کندل...")
        
        results = []
        for symbol in symbols:
            print(f"\n📊 در حال بک‌تست {symbol}...")
            df_h4 = self.fetcher.get_candles(symbol, settings.TIMEFRAME_STRUCTURE, limit=limit)
            
            if df_h4 is None or len(df_h4) < 100:
                print(f"   ⚠️ دیتای کافی برای {symbol} یافت نشد.")
                continue
                
            bullish_obs, bearish_obs = self.detector.find_order_blocks(df_h4)
            wins = 0
            losses = 0
            
            print(f"   🧱 {len(bullish_obs)} OB صعودی و {len(bearish_obs)} OB نزولی در گذشته یافت شد.")
            
            # ================= بررسی اوردربلاک‌های صعودی =================
            for ob in bullish_obs:
                # 🚀 نکته: ما شرط Mitigated بودن را حذف کردیم تا معاملات گذشته را ببینیم!
                ob_index = df_h4.index.get_loc(ob['timestamp'])
                df_future = df_h4.iloc[ob_index + 3:] 
                
                # پیدا کردن اولین برخورد قیمت به اوردربلاک (نقطه ورود)
                entry_candle_idx = None
                for idx, candle in df_future.iterrows():
                    if candle['low'] <= ob['top']:
                        entry_candle_idx = idx
                        break
                
                if entry_candle_idx is None:
                    # قیمت هرگز در گذشته به این اوردربلاک برنگشته است
                    continue
                    
                # بررسی القا (Inducement): آیا بین زمان تشکیل OB و زمان ورود، تله‌ای ساخته شد؟
                df_before_entry = df_h4.loc[ob['timestamp']:entry_candle_idx]
                if not self.analyzer.check_inducement(df_before_entry, ob['timestamp'], "Bullish"):
                    continue
                    
                print(f"      🟢 [ورود خرید] برخورد به OB صعودی در زمان {entry_candle_idx}")
                
                # بررسی آینده بعد از ورود برای یافتن حد سود یا حد ضرر
                df_after_entry = df_h4.loc[entry_candle_idx:]
                risk = ob['top'] - ob['bottom']
                target = ob['top'] + (risk * 2) # ریسک به ریوارد 1:2
                
                for idx, candle in df_after_entry.iterrows():
                    if candle['low'] < ob['bottom']:
                        losses += 1
                        print("         ❌ استاپ‌لاس خورد.")
                        break
                    if candle['high'] >= target:
                        wins += 1
                        print("         ✅ تارگت (TP) تاچ شد.")
                        break

            # ================= بررسی اوردربلاک‌های نزولی =================
            for ob in bearish_obs:
                ob_index = df_h4.index.get_loc(ob['timestamp'])
                df_future = df_h4.iloc[ob_index + 3:] 
                
                entry_candle_idx = None
                for idx, candle in df_future.iterrows():
                    if candle['high'] >= ob['bottom']:
                        entry_candle_idx = idx
                        break
                
                if entry_candle_idx is None:
                    continue
                    
                df_before_entry = df_h4.loc[ob['timestamp']:entry_candle_idx]
                if not self.analyzer.check_inducement(df_before_entry, ob['timestamp'], "Bearish"):
                    continue
                    
                print(f"      🔴 [ورود فروش] برخورد به OB نزولی در زمان {entry_candle_idx}")
                
                df_after_entry = df_h4.loc[entry_candle_idx:]
                risk = ob['top'] - ob['bottom']
                target = ob['bottom'] - (risk * 2) # ریسک به ریوارد 1:2
                
                for idx, candle in df_after_entry.iterrows():
                    if candle['high'] > ob['top']:
                        losses += 1
                        print("         ❌ استاپ‌لاس خورد.")
                        break
                    if candle['low'] <= target:
                        wins += 1
                        print("         ✅ تارگت (TP) تاچ شد.")
                        break

            # محاسبه نتیجه
            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            print(f"   🏆 نتیجه {symbol} -> موفق: {wins} | زیان: {losses} | وین‌ریت: {win_rate:.2f}%")
            
            results.append({
                "symbol": symbol,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate
            })

        return results