import time
from settings import settings
from data_fetcher import DataFetcher
from market_structure import MarketStructureAnalyzer
from zone_detector import ZoneDetector
from liquidity_filter import LiquidityAndConfirmationFilter
from risk_manager import RiskManager

def execute_bot_loop():
    print("🚀 ربات هوشمند SMC Toobit فعال شد...")
    
    fetcher = DataFetcher()
    analyzer = MarketStructureAnalyzer()
    detector = ZoneDetector()
    filter_engine = LiquidityAndConfirmationFilter()
    risk_eng = RiskManager()
    
    SIMULATED_BALANCE = 1000.0  # سرمایه فرضی
    
    while True:
        for symbol in settings.WATCHLIST:
            print(f"\n🔍 در حال پردازش {symbol}...")
            
            # دریافت داده‌ها
            df_h4, df_m15 = fetcher.fetch_all_required_data(symbol)
            if df_h4 is None or df_m15 is None: 
                print(f"   ⚠️ خطا: داده‌های H4 یا M15 برای {symbol} دریافت نشد!")
                continue
                
            # تحلیل ساختار
            trend, main_leg, break_type = analyzer.analyze_structure(df_h4)
            print(f"   📊 وضعیت ساختار بازار: {trend} | آخرین شکست: {break_type}")
            
            if trend == "Neutral": 
                print("   ⚠️ روند خنثی است یا سقف/کف معتبر کافی یافت نشد. پرش به ارز بعدی...")
                continue
                
            ote_low, ote_high = detector.calculate_ote_levels(main_leg)
            current_price = df_m15['close'].iloc[-1]
            print(f"   💵 قیمت فعلی M15: {current_price}")
            
            # بررسی پوزیشن خرید
            if trend == "Bullish" and ote_low is not None:
                if ote_low <= current_price <= ote_high:
                    has_swept = filter_engine.check_liquidity_sweep(df_h4, "Bullish")
                    if has_swept and filter_engine.check_m15_confirmation(df_m15, "Bullish"):
                        stop_loss = main_leg["start"] * 0.998 # استاپ پایین لگ
                        pos = risk_eng.calculate_position_size(SIMULATED_BALANCE, current_price, stop_loss)
                        tp1, tp2 = risk_eng.define_trade_targets(current_price, stop_loss, "Bullish")
                        
                        print(f"✅ سیگنال خرید معتبر صادر شد! حجم: {pos} ، تارگت: {tp2}")
            
            # بررسی پوزیشن فروش
            elif trend == "Bearish" and ote_low is not None:
                if ote_low <= current_price <= ote_high:
                    has_swept = filter_engine.check_liquidity_sweep(df_h4, "Bearish")
                    if has_swept and filter_engine.check_m15_confirmation(df_m15, "Bearish"):
                        stop_loss = main_leg["start"] * 1.002
                        pos = risk_eng.calculate_position_size(SIMULATED_BALANCE, current_price, stop_loss)
                        tp1, tp2 = risk_eng.define_trade_targets(current_price, stop_loss, "Bearish")
                        
                        print(f"🔻 سیگنال فروش معتبر صادر شد! حجم: {pos} ، تارگت: {tp2}")
                        
        print("\n⏳ خواب ربات به مدت 5 دقیقه تا پردازش بعدی...")
        time.sleep(300)

if __name__ == "__main__":
    execute_bot_loop()