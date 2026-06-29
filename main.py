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
                
                # ۱. دریافت داده‌ها
                df_h4, df_m15 = fetcher.fetch_all_required_data(symbol)
                if df_h4 is None or df_m15 is None: 
                    continue
                    
                # ۲. تحلیل ساختار بازار
                trend, main_leg, break_type = analyzer.analyze_structure(df_h4)
                if trend == "Neutral" or not main_leg["is_valid"]: 
                    print("   ⚠️ روند خنثی است یا لگ نامعتبر است.")
                    continue
                    
                # چاپ اطلاعات شفاف از تشخیص لگ ربات
                print(f"   📊 روند: {trend} | شروع لگ: {main_leg['start']} | پایان لگ: {main_leg['end']} | آخرین شکست: {break_type}")
                    
                # ۳. پیدا کردن اوردربلاک‌های معتبر
                bullish_obs, bearish_obs = detector.find_order_blocks(df_h4)
                current_price = df_m15['close'].iloc[-1]
                print(f"   💵 قیمت فعلی (M15): {current_price}")
                
                # ================= بررسی سیگنال خرید =================
                if trend == "Bullish" and bullish_obs:
                    last_ob = bullish_obs[-1]
                    print(f"   🧱 اوردربلاک صعودی یافت شد (محدوده: {last_ob['bottom']} تا {last_ob['top']}). در حال فیلتر کردن...")
                    
                    if last_ob['is_mitigated']:
                        print("   ❌ رد شد: اوردربلاک مصرف (Mitigate) شده است.")
                        continue
                        
                    in_discount = detector.check_premium_discount(last_ob['top'], main_leg, "Bullish")
                    if not in_discount:
                        print("   ❌ رد شد: قیمت ورود در ناحیه گران (Premium) قرار دارد.")
                        continue
                        
                    has_inducement = analyzer.check_inducement(df_h4, last_ob['timestamp'], "Bullish")
                    if not has_inducement:
                        print("   ❌ رد شد: فاقد تله القا (Inducement).")
                        continue

                    # اگر از فیلترهای بالا عبور کند، یعنی OB طلایی و آماده است!
                    if last_ob['bottom'] <= current_price <= last_ob['top'] * 1.01:
                        is_cbs = filter_engine.check_cbs_entry(df_h4, "Bullish")
                        is_choch = filter_engine.check_choch_entry(df_m15, "Bullish")
                        
                        if is_cbs or is_choch:
                            entry_type = "CBS" if is_cbs else "CHoCH"
                            stop_loss = last_ob['bottom'] * 0.998
                            pos_size = risk_eng.calculate_position_size(SIMULATED_BALANCE, current_price, stop_loss)
                            tp1, tp2 = risk_eng.define_trade_targets(current_price, stop_loss, "Bullish")
                            print(f"   ✅ سیگنال خرید ({entry_type}) صادر شد! حجم: {pos_size} ، تارگت: {tp2}")
                        else:
                            print("   ⏳ قیمت در ناحیه است اما منتظر تاییدیه M15 (پوشا+حجم) یا CBS هستیم...")
                    else:
                        print(f"   🎯 اوردربلاک طلایی و معتبر است! اما قیمت هنوز به آن نرسیده. (فاصله: {abs(current_price - last_ob['top']):.4f} دلار)")
                
                # ================= بررسی سیگنال فروش =================
                elif trend == "Bearish" and bearish_obs:
                    last_ob = bearish_obs[-1]
                    print(f"   🧱 اوردربلاک نزولی یافت شد (محدوده: {last_ob['bottom']} تا {last_ob['top']}). در حال فیلتر کردن...")
                    
                    if last_ob['is_mitigated']:
                        print("   ❌ رد شد: اوردربلاک مصرف شده است.")
                        continue
                        
                    in_premium = detector.check_premium_discount(last_ob['bottom'], main_leg, "Bearish")
                    if not in_premium:
                        print("   ❌ رد شد: قیمت در ناحیه ارزان (Discount) است. فروش ممنوع!")
                        continue
                        
                    has_inducement = analyzer.check_inducement(df_h4, last_ob['timestamp'], "Bearish")
                    if not has_inducement:
                        print("   ❌ رد شد: فاقد القا (Inducement).")
                        continue

                    # بررسی برخورد قیمت به OB
                    if last_ob['bottom'] * 0.99 <= current_price <= last_ob['top']:
                        is_cbs = filter_engine.check_cbs_entry(df_h4, "Bearish")
                        is_choch = filter_engine.check_choch_entry(df_m15, "Bearish")
                        
                        if is_cbs or is_choch:
                            entry_type = "CBS" if is_cbs else "CHoCH"
                            stop_loss = last_ob['top'] * 1.002 
                            pos_size = risk_eng.calculate_position_size(SIMULATED_BALANCE, current_price, stop_loss)
                            tp1, tp2 = risk_eng.define_trade_targets(current_price, stop_loss, "Bearish")
                            print(f"   🔻 سیگنال فروش ({entry_type}) صادر شد! حجم: {pos_size} ، تارگت: {tp2}")
                        else:
                            print("   ⏳ قیمت در ناحیه است اما منتظر تاییدیه M15 (پوشا+حجم) یا CBS هستیم...")
                    else:
                        print(f"   🎯 اوردربلاک طلایی و معتبر است! اما قیمت هنوز به آن نرسیده. (فاصله: {abs(current_price - last_ob['bottom']):.4f} دلار)")
                            
            now = datetime.now().strftime("%H:%M:%S")
            bot_state["last_update"] = f"آخرین پردازش: {now}"
            bot_state["status"] = "آماده به کار ✅"
            await manager.broadcast(bot_state)
            
            # خواب ربات را به 10 ثانیه کاهش دادیم تا زنده بماند
            print(f"\n⏳ استراحت کوتاه ربات... ({now})")
            await asyncio.sleep(10) 
            
        except Exception as e:
            bot_state["status"] = "خطا در پردازش ❌"
            await manager.broadcast(bot_state)
            print(f"Error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(execute_bot_loop())