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
                
                # ترکیب و مرتب‌سازی اوردربلاک‌ها برای ارسال به فرانت‌اند
                # ترکیب و مرتب‌سازی اوردربلاک‌ها برای ارسال به فرانت‌اند
                all_obs = bullish_obs + bearish_obs
                processed_obs = []
                
                for ob in all_obs:
                    dist = current_price - ob['top'] if ob['type'] == 'Bullish' else ob['bottom'] - current_price
                    dist = abs(dist)
                    
                    # محاسبه TP، SL و لوریج پیشنهادی
                    if ob['type'] == 'Bullish':
                        entry = ob['top']
                        sl = ob['bottom']
                        tp = entry + ((entry - sl) * 2) # ریوارد 2
                    else:
                        entry = ob['bottom']
                        sl = ob['top']
                        tp = entry - ((sl - entry) * 2) # ریوارد 2
                        
                    # محاسبه لوریج ایمن (فاصله استاپ تا نقطه ورود)
                    sl_dist_pct = abs(entry - sl) / entry * 100
                    safe_leverage = max(1, min(50, int(15 / sl_dist_pct))) if sl_dist_pct > 0 else 1
                    
                    processed_obs.append({
                        "type": ob['type'],
                        "top": round(ob['top'], 4),
                        "bottom": round(ob['bottom'], 4),
                        "tp": round(tp, 4),
                        "sl": round(sl, 4),
                        "leverage": safe_leverage,
                        "is_mitigated": ob['is_mitigated'],
                        "distance": round(dist, 4),
                        "timestamp": str(ob['timestamp']),
                        "note": ob['note']
                    })
                
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