import time
import asyncio
from datetime import datetime
from settings import settings
from data_fetcher import DataFetcher
from market_structure import MarketStructureAnalyzer
from zone_detector import ZoneDetector
from liquidity_filter import LiquidityAndConfirmationFilter
from risk_manager import RiskManager
from shared_state import bot_state  # <--- اضافه کردن حافظه مشترک
from ws_manager import manager
async def execute_bot_loop():
    print("🚀 موتور تحلیلگر SMC ناهمگام (Async) فعال شد...")
    
    fetcher = DataFetcher()
    analyzer = MarketStructureAnalyzer()
    detector = ZoneDetector()
    filter_engine = LiquidityAndConfirmationFilter()
    risk_eng = RiskManager()
    
    bot_state["active_pairs"] = settings.WATCHLIST
    
    while True:
        try:
            # 1. آپدیت وضعیت و ارسال آنی به فرانت‌اند
            bot_state["status"] = "در حال پردازش بازار ⏳"
            await manager.broadcast(bot_state)
            
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
                await asyncio.sleep(0.1)              
            now = datetime.now().strftime("%H:%M:%S")
            bot_state["last_update"] = f"آخرین پردازش: {now}"
            bot_state["status"] = "آماده به کار ✅"
            await manager.broadcast(bot_state)
            
            print(f"⏳ خواب ربات به مدت 5 دقیقه... ({now})")
            # به جای time.sleep از نسخه async استفاده می‌کنیم تا وب‌سرور متوقف نشود
            await asyncio.sleep(300) 
            
        except Exception as e:
            bot_state["status"] = "خطا در پردازش ❌"
            await manager.broadcast(bot_state)
            print(f"Error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    execute_bot_loop()