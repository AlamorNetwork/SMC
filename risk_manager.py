from settings import settings

class RiskManager:
    def calculate_position_size(self, account_balance, entry_price, stop_loss_price):
        try:
            if entry_price == stop_loss_price: return 0.0
            
            risk_amount_usd = account_balance * (settings.RISK_PERCENT / 100.0)
            loss_per_unit = abs(entry_price - stop_loss_price)
            position_size = risk_amount_usd / loss_per_unit
            
            return round(position_size, 4)
        except:
            return 0.0

    def define_trade_targets(self, entry_price, stop_loss_price, direction):
        risk_distance = abs(entry_price - stop_loss_price)
        if direction == "Bullish":
            return round(entry_price + (risk_distance * 2.0), 4), round(entry_price + (risk_distance * 3.0), 4)
        else:
            return round(entry_price - (risk_distance * 2.0), 4), round(entry_price - (risk_distance * 3.0), 4)