# strategy.py
from configuration import Config
from utils import check_engulfing

class BiTimeframeStrategy:
    """
    Pure Strategy Class.
    Decoupled from any backtesting library.
    Used by both CustomBacktester and LiveTrader.
    """
    
    @staticmethod
    def get_signal(opens, highs, lows, closes, closes_1h, emas_1h):
        """
        DETERMINISTIC LOGIC [cite: 21]
        Returns: (Signal, SL, TP)
        """
        # Need at least 2 candles
        if len(closes) < 2: return None, None, None
        # 1. 1H Trend Filter
        # We look at the last CLOSED 1H candle (aligned via ffill in utils)
        trend_bullish = closes_1h[-2] > emas_1h[-2]
        trend_bearish = closes_1h[-2] < emas_1h[-2]

        # 2. 5M Trigger (Engulfing)
        curr_o, curr_c = opens[-2], closes[-2]
        prev_o, prev_c = opens[-3], closes[-3]
        prev_h, prev_l = highs[-3], lows[-3]
        curr_h, curr_l = highs[-2], lows[-2]
        # --- LONG LOGIC ---
        if trend_bullish:
            if check_engulfing(curr_o, curr_c, prev_o, prev_c, 'BULLISH'):
                sl = curr_l # SL = closed Candle Low
                risk = opens[-1] - sl
                if risk <= 0: return None, None, None # Safety
                tp = opens[-1] + (risk * Config.RR_RATIO)
                return 'BUY', sl, tp

        # --- SHORT LOGIC ---
        elif trend_bearish:
            if check_engulfing(curr_o, curr_c, prev_o, prev_c, 'BEARISH'):
                sl = curr_h  # SL = closed Candle High
                risk = sl - opens[-1]
                if risk <= 0: return None, None, None # Safety
                tp = opens[-1] - (risk * Config.RR_RATIO)
                return 'SELL', sl, tp

        return None, None, None
    
    @staticmethod
    def get_position_size(entry_price, sl_price, capital_to_risk):
        """
        DETERMINISTIC SIZING LOGIC
        Calculates quantity based on Risk Amount / Distance.
        """
        distance = abs(entry_price - sl_price)
        
        if distance == 0: return 0
        
        # Quantity = Risk ($) / Distance ($)
        quantity = capital_to_risk / distance 
        
        return quantity
    
    @staticmethod
    def check_exit(direction, sl, tp, low_price, high_price):
        """
        DETERMINISTIC EXIT LOGIC
        Checks if price action hit SL or TP.
        
        Args:
            low_price: Candle Low (Backtest) or Current Price (Live)
            high_price: Candle High (Backtest) or Current Price (Live)
        """
        if direction == 'BUY':
            if low_price <= sl:
                return 'SL'
            elif high_price >= tp:
                return 'TP'
                
        elif direction == 'SELL':
            if high_price >= sl:
                return 'SL'
            elif low_price <= tp:
                return 'TP'
                
        return None