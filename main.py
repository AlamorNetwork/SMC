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
            bot_state["alarm_trigger"] = False # ریست کردن آلارم در هر چرخه
            await manager.broadcast(bot_state)
            
            for symbol in bot_state["active_pairs"]:
                # دریافت داده‌ها
                df_h4, df_m15 = fetcher.fetch_all_required_data(symbol)
                if df_h4 is None or df_m15 is None:
                    continue
                    
                trend, main_leg, break_type = analyzer.analyze_structure(df_h4)
                if trend == "Neutral" or not main_leg["is_valid"]: 
                    bot_state["market_data"][symbol] = {"trend": "Neutral", "price": "-", "msg": "روند خنثی", "obs": []}
                    continue
                    
                current_price = df_m15['close'].iloc[-1]
                bullish_obs, bearish_obs = detector.find_order_blocks(df_h4)
                
                # ========================================================
                # 🧠 پردازشگر چندگانه (Multi-Timeframe Processor) در حالت لایو
                # ========================================================
                all_obs = bullish_obs + bearish_obs
                processed_obs = []
                
                # 🚀 تغییر مهم: افزایش دریافت کندل‌های M15 تا 2000 تا که تاریخچه OBهای 4 ساعته را پوشش دهد
                df_m15 = fetcher.get_candles(symbol, settings.TIMEFRAME_ENTRY, limit=2000)
                bullish_m15_obs, bearish_m15_obs = detector.find_order_blocks(df_m15) if df_m15 is not None else ([], [])
                
                for ob in all_obs:
                    # فاصله قیمت فعلی تا اوردربلاک H4
                    dist = current_price - ob['top'] if ob['type'] == 'Bullish' else ob['bottom'] - current_price
                    dist = abs(dist)
                    
                    # مقادیر اولیه (اگر OB پانزده دقیقه‌ای پیدا نشد، همان H4 را نگه می‌داریم)
                    entry_price = ob['top'] if ob['type'] == 'Bullish' else ob['bottom']
                    sl_price = ob['bottom'] if ob['type'] == 'Bullish' else ob['top']
                    status_note = ob.get('note', '') 
                    
                    # 🎯 عملیات OB Refinement (بهینه‌سازی ناحیه 4 ساعته به 15 دقیقه)
                    refined = False
                    
                    if ob['type'] == 'Bullish':
                        # پیدا کردن تمام OBهای 15 دقیقه‌ای که از نظر قیمتی "درون" باکس 4 ساعته قرار دارند
                        valid_m15s = [
                            m for m in bullish_m15_obs 
                            if m['bottom'] >= (ob['bottom'] - (ob['bottom']*0.001)) and m['top'] <= (ob['top'] + (ob['top']*0.002))
                        ]
                        
                        if valid_m15s:
                            # 🥇 انتخاب پایین‌ترین (بهترین و کم‌ریسک‌ترین) OB پانزده دقیقه در آن ناحیه
                            best_m15 = sorted(valid_m15s, key=lambda x: x['bottom'])[0]
                            entry_price = best_m15['top'] 
                            buffer = best_m15['bottom'] * 0.0015 # سپر محافظتی استاپ
                            sl_price = best_m15['bottom'] - buffer 
                            status_note = "🎯 ناحیه به M15 بهینه‌سازی شد (Sniper OB)"
                            refined = True
                            
                        tp_price = entry_price + ((entry_price - sl_price) * 3) # ریوارد ثابت 1:3
                        
                    else: # Bearish
                        valid_m15s = [
                            m for m in bearish_m15_obs 
                            if m['top'] <= (ob['top'] + (ob['top']*0.001)) and m['bottom'] >= (ob['bottom'] - (ob['bottom']*0.002))
                        ]
                        
                        if valid_m15s:
                            # 🥇 انتخاب بالاترین OB پانزده دقیقه
                            best_m15 = sorted(valid_m15s, key=lambda x: x['top'], reverse=True)[0]
                            entry_price = best_m15['bottom']
                            buffer = best_m15['top'] * 0.0015 
                            sl_price = best_m15['top'] + buffer 
                            status_note = "🎯 ناحیه به M15 بهینه‌سازی شد (Sniper OB)"
                            refined = True
                            
                        tp_price = entry_price - ((sl_price - entry_price) * 3)

                    # اگر ناحیه بهینه نشد، یک پیام به کاربر می‌دهیم
                    if not refined and "طلایی" not in status_note and "SMT" not in status_note:
                        status_note = "ناحیه H4 (در انتظار تایید M15)"

                    # محاسبه لوریج ایمن بر اساس استاپ‌لاس
                    sl_dist_pct = abs(entry_price - sl_price) / entry_price * 100
                    safe_leverage = max(1, min(100, int(15 / sl_dist_pct))) if sl_dist_pct > 0 else 1
                    
                    processed_obs.append({
                        "type": ob['type'],
                        "top": round(entry_price, 4),      # این همان نقطه ورود نهایی ماست
                        "bottom": round(entry_price, 4),   # برای سازگاری با فرانت‌اند
                        "tp": round(tp_price, 4),
                        "sl": round(sl_price, 4),
                        "leverage": safe_leverage,
                        "is_mitigated": ob['is_mitigated'],
                        "distance": round(dist, 4),
                        "timestamp": str(ob['timestamp']),
                        "note": status_note
                    })
                
                # مرتب‌سازی بر اساس فاصله تا قیمت زنده
                processed_obs = sorted(processed_obs, key=lambda x: x['distance'])
                
                status_msg = "در حال رصد بازار..."
                color_class = "text-blue-400"

                # بررسی سیگنال روی نزدیک‌ترین اوردربلاک معتبر
                if trend == "Bullish" and bullish_obs:
                    last_ob = bullish_obs[-1]
                    if not last_ob['is_mitigated'] and detector.check_premium_discount(last_ob['top'], main_leg, "Bullish") and analyzer.check_inducement(df_h4, last_ob['timestamp'], "Bullish"):
                        if last_ob['bottom'] <= current_price <= last_ob['top'] * 1.01:
                            if filter_engine.check_cbs_entry(df_h4, "Bullish") or filter_engine.check_choch_entry(df_m15, "Bullish"):
                                status_msg = "✅ سیگنال خرید صادر شد!"
                                color_class = "text-emerald-400"
                                bot_state["alarm_trigger"] = True
                                bot_state["alarm_symbol"] = symbol
                            else:
                                status_msg = "⏳ قیمت رسید! منتظر تاییدیه M15"
                                color_class = "text-yellow-400"
                                bot_state["alarm_trigger"] = True # آلارم برخورد به ناحیه
                                bot_state["alarm_symbol"] = symbol
                                
                elif trend == "Bearish" and bearish_obs:
                    last_ob = bearish_obs[-1]
                    if not last_ob['is_mitigated'] and detector.check_premium_discount(last_ob['bottom'], main_leg, "Bearish") and analyzer.check_inducement(df_h4, last_ob['timestamp'], "Bearish"):
                        if last_ob['bottom'] * 0.99 <= current_price <= last_ob['top']:
                            if filter_engine.check_cbs_entry(df_h4, "Bearish") or filter_engine.check_choch_entry(df_m15, "Bearish"):
                                status_msg = "🔻 سیگنال فروش صادر شد!"
                                color_class = "text-rose-400"
                                bot_state["alarm_trigger"] = True
                                bot_state["alarm_symbol"] = symbol
                            else:
                                status_msg = "⏳ قیمت رسید! منتظر تاییدیه M15"
                                color_class = "text-yellow-400"
                                bot_state["alarm_trigger"] = True
                                bot_state["alarm_symbol"] = symbol

                bot_state["market_data"][symbol] = {
                    "trend": trend,
                    "price": f"{current_price:.4f}",
                    "msg": status_msg,
                    "color": color_class,
                    "obs": processed_obs  # ارسال لیست کامل به فرانت‌اند
                }
                            
            now = datetime.now().strftime("%H:%M:%S")
            bot_state["last_update"] = f"آخرین بروزرسانی: {now}"
            bot_state["status"] = "آماده شکار ✅"
            
            await manager.broadcast(bot_state)
            await asyncio.sleep(10) 
            
        except Exception as e:
            bot_state["status"] = "خطا در پردازش ❌"
            await manager.broadcast(bot_state)
            print(f"Error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(execute_bot_loop())