import asyncio
from datetime import datetime
from settings import settings
from data_fetcher import DataFetcher
from market_structure import MarketStructureAnalyzer
from zone_detector import ZoneDetector
from liquidity_filter import LiquidityAndConfirmationFilter
from risk_manager import RiskManager
from shared_state import bot_state
from ws_manager import manager

SIMULATED_BALANCE = 1000.0  # سرمایه فرضی برای تست

async def execute_bot_loop():
    print("🚀 موتور تحلیلگر پیشرفته SMC فعال شد...")
    
    fetcher = DataFetcher()
    analyzer = MarketStructureAnalyzer()
    detector = ZoneDetector()
    filter_engine = LiquidityAndConfirmationFilter()
    risk_eng = RiskManager()
    
    # واچ‌لیست ارزهایی که اینجا یا در settings تعریف کردی را بررسی می‌کند
    bot_state["active_pairs"] = settings.WATCHLIST
    
    while True:
        try:
            bot_state["status"] = "در حال پردازش بازار ⏳"
            await manager.broadcast(bot_state)
            
            for symbol in settings.WATCHLIST:
                print(f"\n🔍 در حال پردازش {symbol}...")
                
                # دریافت داده‌ها
                df_h4, df_m15 = fetcher.fetch_all_required_data(symbol)
                if df_h4 is None or df_m15 is None:
                    bot_state["market_data"][symbol] = {"trend": "Error", "price": "-", "msg": "خطا در دریافت دیتا", "color": "text-red-500"}
                    continue
                    
                trend, main_leg, break_type = analyzer.analyze_structure(df_h4)
                if trend == "Neutral" or not main_leg["is_valid"]: 
                    msg = "روند خنثی یا لگ نامعتبر"
                    print(f"   ⚠️ {msg}")
                    bot_state["market_data"][symbol] = {"trend": "Neutral", "price": "-", "msg": msg, "color": "text-gray-400"}
                    continue
                    
                current_price = df_m15['close'].iloc[-1]
                bullish_obs, bearish_obs = detector.find_order_blocks(df_h4)
                
                status_msg = "در حال جستجوی اوردربلاک..."
                color_class = "text-blue-400"

                # ================= بررسی سیگنال خرید =================
                if trend == "Bullish" and bullish_obs:
                    last_ob = bullish_obs[-1]
                    if last_ob['is_mitigated']:
                        status_msg = "اوردربلاک صعودی مصرف شده (Mitigated) ❌"
                        color_class = "text-red-400"
                    elif not detector.check_premium_discount(last_ob['top'], main_leg, "Bullish"):
                        status_msg = "قیمت در ناحیه گران (Premium) است ❌"
                        color_class = "text-orange-400"
                    elif not analyzer.check_inducement(df_h4, last_ob['timestamp'], "Bullish"):
                        status_msg = "فاقد تله القا (Inducement) ❌"
                        color_class = "text-orange-400"
                    elif last_ob['bottom'] <= current_price <= last_ob['top'] * 1.01:
                        if filter_engine.check_cbs_entry(df_h4, "Bullish") or filter_engine.check_choch_entry(df_m15, "Bullish"):
                            status_msg = "✅ سیگنال خرید صادر شد!"
                            color_class = "text-emerald-400"
                            bot_state["signals_today"] += 1
                        else:
                            status_msg = "⏳ منتظر تاییدیه M15 (پوشا+حجم)"
                            color_class = "text-yellow-400"
                    else:
                        dist = abs(current_price - last_ob['top'])
                        status_msg = f"🎯 اوردربلاک طلایی معتبر! فاصله: {dist:.4f}"
                        color_class = "text-emerald-400"

                # ================= بررسی سیگنال فروش =================
                elif trend == "Bearish" and bearish_obs:
                    last_ob = bearish_obs[-1]
                    if last_ob['is_mitigated']:
                        status_msg = "اوردربلاک نزولی مصرف شده (Mitigated) ❌"
                        color_class = "text-red-400"
                    elif not detector.check_premium_discount(last_ob['bottom'], main_leg, "Bearish"):
                        status_msg = "قیمت در ناحیه ارزان (Discount) است ❌"
                        color_class = "text-orange-400"
                    elif not analyzer.check_inducement(df_h4, last_ob['timestamp'], "Bearish"):
                        status_msg = "فاقد تله القا (Inducement) ❌"
                        color_class = "text-orange-400"
                    elif last_ob['bottom'] * 0.99 <= current_price <= last_ob['top']:
                        if filter_engine.check_cbs_entry(df_h4, "Bearish") or filter_engine.check_choch_entry(df_m15, "Bearish"):
                            status_msg = "🔻 سیگنال فروش صادر شد!"
                            color_class = "text-rose-400"
                            bot_state["signals_today"] += 1
                        else:
                            status_msg = "⏳ منتظر تاییدیه M15 (پوشا+حجم)"
                            color_class = "text-yellow-400"
                    else:
                        dist = abs(current_price - last_ob['bottom'])
                        status_msg = f"🎯 اوردربلاک طلایی معتبر! فاصله: {dist:.4f}"
                        color_class = "text-rose-400"

                # ذخیره اطلاعات برای ارسال به وب‌سایت
                bot_state["market_data"][symbol] = {
                    "trend": trend,
                    "price": f"{current_price:.4f}",
                    "msg": status_msg,
                    "color": color_class
                }
                print(f"   {status_msg}")
                            
            now = datetime.now().strftime("%H:%M:%S")
            bot_state["last_update"] = f"آخرین بروزرسانی: {now}"
            bot_state["status"] = "آماده شکار ✅"
            
            # ارسال تمام دیتاها (از جمله مارکت دیتا) به فرانت‌اند
            await manager.broadcast(bot_state)
            
            print(f"\n⏳ استراحت کوتاه ربات... ({now})")
            await asyncio.sleep(10) 
            
        except Exception as e:
            bot_state["status"] = "خطا در پردازش ❌"
            await manager.broadcast(bot_state)
            print(f"Error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(execute_bot_loop())