import numpy as np
from scipy.stats import norm

class BlackScholesModel:
    """
    ماژول محاسبه قیمت اختیار معامله (Options) بر اساس مدل بلک-شولز
    """
    
    def __init__(self, S, K, T, r, sigma):
        """
        تعریف پارامترهای اصلی:
        S (Stock Price): قیمت فعلی دارایی پایه (مثلا قیمت فعلی بیت‌کوین)
        K (Strike Price): قیمت اعمال قرارداد
        T (Time to Maturity): زمان باقی‌مانده تا انقضا (بر حسب سال، مثلا 0.5 یعنی ۶ ماه)
        r (Risk-free Rate): نرخ بهره بدون ریسک (به اعشار، مثلا 0.05 برای 5 درصد)
        sigma (Volatility): نوسانات سالانه دارایی (به اعشار، مثلا 0.2 برای 20 درصد)
        """
        self.S = float(S)
        self.K = float(K)
        self.T = float(T)
        self.r = float(r)
        self.sigma = float(sigma)

    def _calculate_d1_d2(self):
        """
        محاسبه متغیرهای d1 و d2 که در فرمول اصلی استفاده می‌شوند
        """
        # جلوگیری از تقسیم بر صفر در زمان سررسید
        if self.T <= 0:
            return 0.0, 0.0
            
        d1 = (np.log(self.S / self.K) + (self.r + 0.5 * self.sigma ** 2) * self.T) / (self.sigma * np.sqrt(self.T))
        d2 = d1 - self.sigma * np.sqrt(self.T)
        return d1, d2

    def calculate_call_price(self):
        """
        محاسبه قیمت قرارداد اختیار خرید (Call Option)
        """
        if self.T <= 0:
            return max(0.0, self.S - self.K)
            
        d1, d2 = self._calculate_d1_d2()
        call_price = (self.S * norm.cdf(d1, 0.0, 1.0)) - (self.K * np.exp(-self.r * self.T) * norm.cdf(d2, 0.0, 1.0))
        return round(call_price, 4)

    def calculate_put_price(self):
        """
        محاسبه قیمت قرارداد اختیار فروش (Put Option)
        """
        if self.T <= 0:
            return max(0.0, self.K - self.S)
            
        d1, d2 = self._calculate_d1_d2()
        put_price = (self.K * np.exp(-self.r * self.T) * norm.cdf(-d2, 0.0, 1.0)) - (self.S * norm.cdf(-d1, 0.0, 1.0))
        return round(put_price, 4)

# --- بخش تست کد ---
if __name__ == "__main__":
    # مثال: بیت کوین در قیمت ۶۰,۰۰۰ دلار، اعمال روی ۶۵,۰۰۰، تا ۳ ماه دیگر (0.25 سال)
    bsm = BlackScholesModel(S=60000, K=65000, T=0.25, r=0.05, sigma=0.3)
    
    print(f"💰 قیمت منصفانه اختیار خرید (Call): {bsm.calculate_call_price()} دلار")
    print(f"📉 قیمت منصفانه اختیار فروش (Put): {bsm.calculate_put_price()} دلار")