import time
import math
import pandas as pd
import requests
import hmac
import hashlib
from datetime import datetime, timedelta
from configuration import Config
from strategy import BiTimeframeStrategy
from utils import calculate_indicators, setup_logger

# Initialize Logger
logger = setup_logger('LiveTrading')

class BinanceClient:
    def __init__(self):
        # 1. URL for TRADING (Testnet)
        # We use the URL from your Config file for placing orders.
        self.trade_url = Config.TESTNET_BASE_URL
        
        # 2. URL for DATA (Mainnet - Real Money/Charts)
        # We hardcode the live URL here so candles match TradingView.
        self.data_url = "https://fapi.binance.com"
        
        self.headers = {'X-MBX-APIKEY': Config.API_KEY}

    def _sign(self, params):
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(Config.API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        return f"{query_string}&signature={signature}"

    def get_klines(self, symbol, interval, limit=100):
        # FETCH DATA FROM MAINNET (REAL MARKET DATA)
        url = f"{self.data_url}/fapi/v1/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            
            df = pd.DataFrame(data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime', '7', '8', '9', '10', '11'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            df = df[['Open', 'High', 'Low', 'Close']].astype(float)
            return df
        except Exception as e:
            logger.error(f"Error fetching klines from Mainnet: {e}")
            raise e

    def get_current_price(self, symbol):
        # FETCH PRICE FROM MAINNET (REAL MARKET PRICE)
        url = f"{self.data_url}/fapi/v1/ticker/price"
        params = {'symbol': symbol}
        try:
            r = requests.get(url, params=params, timeout=5)
            return float(r.json()['price'])
        except Exception as e:
            logger.error(f"Error fetching price from Mainnet: {e}")
            return None

    def place_order(self, side, quantity):
        # EXECUTE ORDER ON TESTNET (PAPER TRADING)
        url = f"{self.trade_url}/api/v3/order"
        
        params = {
            'symbol': Config.SYMBOL,
            'side': side,
            'type': 'MARKET',
            'quantity': round(quantity, 3),
            'timestamp': int(time.time() * 1000)
        }
        
        query = self._sign(params)
        try:
            r = requests.post(f"{url}?{query}", headers=self.headers, timeout=5)
            res_json = r.json()
            
            if 'orderId' in res_json:
                logger.info(f"ORDER FILLED (Testnet): {side} {quantity} @ Market")
                return True
            else:
                logger.error(f"Order Failed: {res_json}")
                return False
        except Exception as e:
            logger.error(f"Order execution error: {e}")
            return False

def get_seconds_to_next_candle():
    """Calculates seconds remaining until the next 5-minute mark."""
    now = datetime.now()
    minutes_to_next = 5 - (now.minute % 5)
    target_time = now + timedelta(minutes=minutes_to_next)
    target_time = target_time.replace(second=0, microsecond=0)
    
    seconds_remaining = (target_time - now).total_seconds()
    return max(seconds_remaining, 1)

def run_live():
    client = BinanceClient()
    logger.info(f"Starting Live Trading on {Config.SYMBOL} (Hybrid Mode: Real Data / Testnet Execution)")
    
    current_position = None 
    INITIAL_CAPITAL = 10000 

    while True:
        try:
            # --- PHASE 1: MONITOR OPEN TRADE (FAST LOOP) ---
            if current_position:
                # Get Real Market Price for Signal Check
                current_price = client.get_current_price(Config.SYMBOL)
                
                if current_price:
                    exit_reason = BiTimeframeStrategy.check_exit(
                        current_position['type'],
                        current_position['sl'],
                        current_position['tp'],
                        low_price=current_price, 
                        high_price=current_price
                    )
                    
                    if exit_reason:
                        logger.info(f"EXIT SIGNAL: {exit_reason} at {current_price}")
                        close_side = 'SELL' if current_position['type'] == 'BUY' else 'BUY'
                        
                        # Execute Exit on Testnet
                        if client.place_order(close_side, current_position['size']):
                            with open(Config.LIVE_OUTPUT, 'a') as f:
                                f.write(f"{datetime.now()},{Config.SYMBOL},{close_side},{current_position['entry']},{current_price},{exit_reason}\n")
                            current_position = None 
                    else:
                        logger.info(f"In Trade. Price: {current_price} (SL: {current_position['sl']} TP: {current_position['tp']})")
                
                time.sleep(60) 
                continue 

            # --- PHASE 2: WAIT FOR CANDLE CLOSE (SYNC LOOP) ---
            wait_seconds = get_seconds_to_next_candle()
            logger.info(f"Waiting {wait_seconds:.0f}s for next 5m candle close...")
            time.sleep(wait_seconds)
            
            logger.info("Candle Closed. Fetching Data...")
            time.sleep(5) # Buffer for API to update

            # --- PHASE 3: FETCH & PRINT DATA ---
            # These now fetch from MAINNET
            df_5m = client.get_klines(Config.SYMBOL, Config.TF_ENTRY)
            df_1h = client.get_klines(Config.SYMBOL, Config.TF_FILTER)
            
            data = calculate_indicators(df_5m, df_1h)

            # GRAB THE JUST CLOSED CANDLE (Index -2)
            closed_candle = data.iloc[-2]
            
            # 1. Print 1H Trend Status
            trend_price = closed_candle['Close_1h']
            trend_ema = closed_candle['EMA_21_1h']
            trend_dir = "BULLISH" if trend_price > trend_ema else "BEARISH"
            
            logger.info("------------------------------------------------")
            logger.info(f"1H TREND CHECK ({closed_candle.name})")
            logger.info(f"   1H Close: {trend_price:.2f}")
            logger.info(f"   1H EMA21: {trend_ema:.2f}")
            logger.info(f"   STATUS  : {trend_dir}")
            
            # 2. Print 5M Candle Data
            logger.info(f"5M CANDLE CHECK")
            logger.info(f"   Open : {closed_candle['Open']:.2f}")
            logger.info(f"   High : {closed_candle['High']:.2f}")
            logger.info(f"   Low  : {closed_candle['Low']:.2f}")
            logger.info(f"   Close: {closed_candle['Close']:.2f}")
            logger.info("------------------------------------------------")

            # --- PHASE 4: CHECK STRATEGY ---
            signal, sl, tp = BiTimeframeStrategy.get_signal(
                data.Open.values[-3:], 
                data.High.values[-3:], 
                data.Low.values[-3:], 
                data.Close.values[-3:],
                data.Close_1h.values[-3:], 
                data.EMA_21_1h.values[-3:]
            )

            print(f"Signal: {signal}, SL: {sl}, TP: {tp}")

            if signal:
                logger.info(f"SIGNAL DETECTED: {signal}")
                entry_price = closed_candle['Close']
                risk_amt = INITIAL_CAPITAL * Config.RISK_PER_TRADE
                quantity = BiTimeframeStrategy.get_position_size(entry_price, sl, risk_amt)
                
                if signal == 'SELL':
                    print("Short trades not supported in Spot Testnet. Skipping...")
                    logger.warning("Skipped SELL signal (Spot Long-Only Mode)")
                    continue

                # Execute Entry on Testnet
                if client.place_order(signal, quantity):
                    current_position = {
                        'type': signal,
                        'entry': entry_price,
                        'sl': sl,
                        'tp': tp,
                        'size': quantity
                    }
                    logger.info(f"Entered {signal}. Size: {quantity:.4f}")
            else:
                 logger.info("No Signal. Sleeping...")

        except Exception as e:
            logger.error(f"Error in loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_live()