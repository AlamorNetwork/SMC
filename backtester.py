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
        print(f"🛠 در حال شروع بک‌تست روی {len(symbols)} نماد با {limit} کندل...")
        
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
            
            print(f"   🧱 {len(bullish_obs)} اوردربلاک صعودی و {len(bearish_obs)} نزولی در چارت پیدا شد.")
            
            # بررسی اوردربلاک‌های صعودی
            for ob in bullish_obs:
                if ob['is_mitigated']:
                    print(f"      - [رد شد] اوردربلاک صعودی (زمان: {ob['timestamp']}) قبلاً مصرف (Mitigated) شده بود.")
                    continue
                if not self.analyzer.check_inducement(df_h4, ob['timestamp'], "Bullish"):
                    print(f"      - [رد شد] اوردربلاک صعودی (زمان: {ob['timestamp']}) فاقد تله القا (Inducement) بود.")
                    continue
                    
                print(f"      + [تایید ورود] یک اوردربلاک طلایی صعودی پیدا شد! در حال شبیه‌سازی آینده...")
                ob_index = df_h4.index.get_loc(ob['timestamp'])
                df_future = df_h4.iloc[ob_index + 3:] 
                
                trade_active = False
                for idx, candle in df_future.iterrows():
                    if not trade_active and candle['low'] <= ob['top']:
                        trade_active = True
                        
                    if trade_active:
                        if candle['low'] < ob['bottom']:
                            losses += 1
                            print("         ❌ معامله با استاپ‌لاس بسته شد.")
                            break
                        risk = ob['top'] - ob['bottom']
                        target = ob['top'] + (risk * 2)
                        if candle['high'] >= target:
                            wins += 1
                            print("         ✅ معامله با سود (TP) بسته شد.")
                            break

            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            print(f"   🏆 نتیجه نهایی {symbol} -> موفق: {wins} | زیان: {losses} | وین‌ریت: {win_rate:.2f}%")
            
            results.append({"symbol": symbol, "wins": wins, "losses": losses, "win_rate": win_rate})

        return results

# نحوه اجرای بک‌تست
if __name__ == "__main__":
    backtester = SMCBacktester()
    # می‌توانی فقط نمادهایی که می‌خواهی را اینجا بدهی تا به سرور فشار نیاید
    my_test_list = ["BTC/USDT", "ETH/USDT"] 
    backtester.run_backtest(my_test_list, limit=1000)