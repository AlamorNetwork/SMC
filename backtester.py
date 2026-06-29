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
        """
        آموزش کد: این تابع روی لیست نمادهای دلخواه شما حرکت می‌کند،
        دیتای گذشته را می‌گیرد و عملکرد استراتژی را شبیه‌سازی می‌کند.
        """
        print(f"🛠 در حال شروع بک‌تست روی {len(symbols)} نماد با {limit} کندل...")
        
        results = []
        total_wins = 0
        total_losses = 0
        
        for symbol in symbols:
            print(f"\n📊 در حال بک‌تست {symbol}...")
            # گرفتن دیتای زیاد برای بک‌تست
            df_h4 = self.fetcher.get_candles(symbol, settings.TIMEFRAME_STRUCTURE, limit=limit)
            
            if df_h4 is None or len(df_h4) < 100:
                print(f"   ⚠️ دیتای کافی برای {symbol} یافت نشد.")
                continue
                
            # تحلیل ساختار کل دیتا
            trend, main_leg, _ = self.analyzer.analyze_structure(df_h4)
            bullish_obs, bearish_obs = self.detector.find_order_blocks(df_h4)
            
            # متغیرهای محلی برای این نماد
            wins = 0
            losses = 0
            
            print(f"   🧱 {len(bullish_obs)} اوردربلاک صعودی و {len(bearish_obs)} نزولی در گذشته یافت شد.")
            
            # --- شبیه‌سازی نتایج اوردربلاک‌های صعودی ---
            for ob in bullish_obs:
                # اگر OB فیلترهای ما (القا و بکر بودن) را پاس نکرده باشد، آن را معامله نمی‌کنیم
                if ob['is_mitigated'] or not self.analyzer.check_inducement(df_h4, ob['timestamp'], "Bullish"):
                    continue
                    
                # بررسی اینکه آیا بعد از تشکیل OB، قیمت به تارگت خورده (سود) یا کف OB شکسته شده (ضرر)
                ob_index = df_h4.index.get_loc(ob['timestamp'])
                df_future = df_h4.iloc[ob_index + 3:] # نگاه به آینده بعد از تشکیل OB
                
                trade_active = False
                for idx, candle in df_future.iterrows():
                    # نقطه ورود: برخورد به سقف OB
                    if not trade_active and candle['low'] <= ob['top']:
                        trade_active = True
                        
                    if trade_active:
                        # استاپ لاس: برخورد به پایین OB
                        if candle['low'] < ob['bottom']:
                            losses += 1
                            break
                        # تارگت: رسیدن به ریسک به ریوارد 1:2 (ساده‌سازی شده)
                        risk = ob['top'] - ob['bottom']
                        target = ob['top'] + (risk * 2)
                        if candle['high'] >= target:
                            wins += 1
                            break

            total_wins += wins
            total_losses += losses
            
            # محاسبه وین‌ریت برای هر ارز
            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            print(f"   ✅ معاملات موفق: {wins} | ❌ معاملات زیان‌ده: {losses} | 🏆 وین‌ریت: {win_rate:.2f}%")
            
            results.append({
                "symbol": symbol,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate
            })

        # گزارش نهایی
        print("\n" + "="*40)
        print("📈 گزارش نهایی بک‌تست استراتژی SMC")
        print("="*40)
        overall_trades = total_wins + total_losses
        overall_wr = (total_wins / overall_trades * 100) if overall_trades > 0 else 0
        print(f"کل معاملات: {overall_trades}")
        print(f"وین‌ریت کل سیستم: {overall_wr:.2f}%")
        
        return results

# نحوه اجرای بک‌تست
if __name__ == "__main__":
    backtester = SMCBacktester()
    # می‌توانی فقط نمادهایی که می‌خواهی را اینجا بدهی تا به سرور فشار نیاید
    my_test_list = ["BTC/USDT", "ETH/USDT"] 
    backtester.run_backtest(my_test_list, limit=1000)