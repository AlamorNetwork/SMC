from data_fetcher import DataFetcher
from market_structure import MarketStructureAnalyzer
from zone_detector import ZoneDetector

def run_deep_test(symbol="APE/USDT"):
    print(f"🛠 در حال شروع تست عمیق روی نماد {symbol}...\n")
    
    fetcher = DataFetcher()
    analyzer = MarketStructureAnalyzer()
    detector = ZoneDetector()
    
    df_h4, df_m15 = fetcher.fetch_all_required_data(symbol)
    
    if df_h4 is None:
        print("❌ داده‌ای دریافت نشد.")
        return

    print("--- 📊 گزارش ساختار بازار (تایم‌فریم H4) ---")
    trend, main_leg, break_type = analyzer.analyze_structure(df_h4)
    print(f"🔸 روند فعلی: {trend}")
    print(f"🔸 نوع شکست ساختار اخیر: {break_type}")
    
    if main_leg["start"] is not None:
        print(f"🔸 شروع موج اصلی (Start): {main_leg['start']} | 📅 زمان کندل: {main_leg['start_time']}")
        print(f"🔸 پایان موج اصلی (End): {main_leg['end']}   | 📅 زمان کندل: {main_leg['end_time']}")
        print(f"🔸 وضعیت اعتبار لگ: {'✅ معتبر (Tradeable)' if main_leg['is_valid'] else '❌ نامعتبر (Weak Leg)'}")
        print("   چک‌لیست شروط لگ:")
        for note in main_leg["validation_notes"]:
            print(f"      {note}")
    else:
        print("🔸 لگ اصلی و معتبری یافت نشد.")
    print("-" * 40)

    print("\n--- 🧱 گزارش نواحی معاملاتی (تایم‌فریم H4) ---")
    bullish_obs, bearish_obs = detector.find_order_blocks(df_h4)
    fvgs = detector.find_fvgs(df_h4)
    
    print(f"🔸 تعداد اوردر بلاک‌های صعودی معتبر (با شرط هانت، FVG و قانون شدو): {len(bullish_obs)}")
    if bullish_obs:
        last_bull_ob = bullish_obs[-1]
        print(f"   آخرین OB -> سقف ورود: {last_bull_ob['top']} | کف ورود: {last_bull_ob['bottom']}")
        print(f"   وضعیت شدو: {last_bull_ob['note']} | 📅 زمان: {last_bull_ob['timestamp']}")

    print(f"🔸 تعداد اوردر بلاک‌های نزولی معتبر (با شرط هانت، FVG و قانون شدو): {len(bearish_obs)}")
    if bearish_obs:
        last_bear_ob = bearish_obs[-1]
        print(f"   آخرین OB -> سقف ورود: {last_bear_ob['top']} | کف ورود: {last_bear_ob['bottom']}")
        print(f"   وضعیت شدو: {last_bear_ob['note']} | 📅 زمان: {last_bear_ob['timestamp']}")
        
    print(f"🔸 تعداد گپ‌های ارزش منصفانه (FVG) پیدا شده: {len(fvgs)}")
    print("-" * 40)

    print("\n--- 🎯 گزارش محدوده ورود بهینه (OTE) ---")
    ote_low, ote_high = detector.calculate_ote_levels(main_leg)
    
    if ote_low is not None and ote_high is not None:
        print(f"🔸 محدوده طلایی فیبوناچی بین ۷۱٪ تا ۷۹٪: از {round(ote_low, 4)} تا {round(ote_high, 4)}")
    else:
        print("🔸 خطای محاسبه: موج اصلی معتبر برای رسم فیبوناچی پیدا نشد.")
    print("-" * 40)
    
    print("\n✅ تست با موفقیت به پایان رسید.")

if __name__ == "__main__":
    run_deep_test("APE/USDT")