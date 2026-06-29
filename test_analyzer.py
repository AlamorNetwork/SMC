# test_analyzer.py

from data_fetcher import DataFetcher
from market_structure import MarketStructureAnalyzer
from zone_detector import ZoneDetector

def run_deep_test(symbol="ETH/USDT"):
    """
    تست عمیق ماژول‌های تحلیلی برای اعتبارسنجی فرمول‌ها با چارت واقعی
    """
    print(f"🛠 در حال شروع تست عمیق روی نماد {symbol}...\n")
    
    fetcher = DataFetcher()
    analyzer = MarketStructureAnalyzer()
    detector = ZoneDetector()
    
    # دریافت داده‌ها
    df_h4, df_m15 = fetcher.fetch_all_required_data(symbol)
    
    if df_h4 is None:
        print("❌ داده‌ای دریافت نشد. لطفاً اتصال اینترنت یا کلیدهای صرافی را بررسی کن.")
        return

    # ۱. تست ساختار بازار
    print("--- 📊 گزارش ساختار بازار (تایم‌فریم H4) ---")
    trend, main_leg, break_type = analyzer.analyze_structure(df_h4)
    print(f"🔸 روند فعلی: {trend}")
    print(f"🔸 نوع شکست ساختار اخیر: {break_type}")
    print(f"🔸 نقطه شروع موج اصلی (Start): {main_leg['start']}")
    print(f"🔸 نقطه پایان موج اصلی (End): {main_leg['end']}")
    print("-" * 40)

    # ۲. تست تشخیص نواحی (OB و FVG)
    print("\n--- 🧱 گزارش نواحی معاملاتی (تایم‌فریم H4) ---")
    bullish_obs, bearish_obs = detector.find_order_blocks(df_h4)
    fvgs = detector.find_fvgs(df_h4)
    
    print(f"🔸 تعداد اوردر بلاک‌های صعودی معتبر (با تایید حجم): {len(bullish_obs)}")
    if bullish_obs:
        last_bull_ob = bullish_obs[-1]
        print(f"   آخرین OB صعودی -> سقف: {last_bull_ob['top']} | کف: {last_bull_ob['bottom']}")

    print(f"🔸 تعداد اوردر بلاک‌های نزولی معتبر (با تایید حجم): {len(bearish_obs)}")
    if bearish_obs:
        last_bear_ob = bearish_obs[-1]
        print(f"   آخرین OB نزولی -> سقف: {last_bear_ob['top']} | کف: {last_bear_ob['bottom']}")
        
    print(f"🔸 تعداد گپ‌های ارزش منصفانه (FVG) پیدا شده: {len(fvgs)}")
    print("-" * 40)

    # ۳. تست محدوده‌های فیبوناچی
    print("\n--- 🎯 گزارش محدوده ورود بهینه (OTE) ---")
    ote_low, ote_high = detector.calculate_ote_levels(main_leg)
    
    if ote_low is not None and ote_high is not None:
        print(f"🔸 محدوده طلایی فیبوناچی بین ۶۷٪ تا ۷۱٪: از {round(ote_low, 4)} تا {round(ote_high, 4)}")
    else:
        print("🔸 خطای محاسبه: موج اصلی برای رسم فیبوناچی پیدا نشد.")
    print("-" * 40)
    
    print("\n✅ تست با موفقیت به پایان رسید. اعداد بالا را با چارت خود چک کن.")

if __name__ == "__main__":
    # می‌توانی نماد را در خط زیر تغییر دهی
    run_deep_test("APE/USDT")