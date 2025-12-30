# backtest_runner.py
import pandas as pd
import numpy as np
from configuration import Config
from strategy import BiTimeframeStrategy #using same strategy class
from utils import calculate_indicators, setup_logger

logger = setup_logger('CustomBacktest')

class CustomBacktester:
    def __init__(self, data, initial_capital=10000):
        self.data = data
        self.capital = initial_capital          # Current Balance (Floating)
        self.initial_capital = initial_capital  # Fixed Starting Balance
        self.trades = []
        self.position = None 
        
        # --- NEW: Counter for skipped trades ---
        self.skipped_trades = 0

    def run(self):
        logger.info("Starting Custom Backtest Loop...")
        
        # Convert columns to numpy arrays for speed
        opens = self.data['Open'].values
        highs = self.data['High'].values
        lows = self.data['Low'].values
        closes = self.data['Close'].values
        timestamps = self.data.index
        
        # Indicators
        closes_1h = self.data['Close_1h'].values
        emas_1h = self.data['EMA_21_1h'].values

        # Iterate through candles (start at 2 for lookback)
        for i in range(2, len(self.data)):
            
            # --- 1. MANAGE EXISTING POSITION ---
            # LOGIC: If we are in a trade, we ONLY check for exits.
            # We do NOT check for new signals until this position is closed.
            if self.position:
                trade = self.position
                
                # Check for exit signals (SL or TP)
                exit_reason = BiTimeframeStrategy.check_exit(
                    trade['type'], 
                    trade['sl'], 
                    trade['tp'], 
                    lows[i], 
                    highs[i]
                )

                if exit_reason:
                    # Execute Exit
                    exit_price = trade['sl'] if exit_reason == 'SL' else trade['tp']
                    self.close_trade(timestamps[i], exit_reason, exit_price)
                    # Trade is now closed, self.position is None.
                    # We continue to the next candle to look for new setups.
                    continue 
                else:
                    # CRITICAL: If no exit signal, we are still in the trade.
                    # We 'continue' to the next candle immediately.
                    # This PREVENTS entering a new trade while one is active.
                    continue 

            # --- 2. CHECK FOR NEW SIGNALS ---
            # This block is ONLY reached if self.position is None
            
            # Pass data up to current index i
            signal, sl, tp = BiTimeframeStrategy.get_signal(
                opens[:i+1], highs[:i+1], lows[:i+1], closes[:i+1],
                closes_1h[:i+1], emas_1h[:i+1]
            )

            if signal:
                entry_price = closes[i]
                
                # Risk Calculation (Fixed Risk per Trade)
                risk_amount = self.initial_capital * Config.RISK_PER_TRADE
                sl_distance = abs(entry_price - sl)
                
                # Calculate Size
                if sl_distance > 0:
                    size = risk_amount / sl_distance
                else:
                    size = 0
                
                if size > 0:
                    # Check Insufficient Capital
                    # Cost to open trade (Spot) = Price * Size
                    trade_cost = entry_price * size
                    
                    if self.capital >= trade_cost:
                        self.position = {
                            'entry_time': timestamps[i],
                            'symbol': Config.SYMBOL,
                            'type': signal,
                            'entry': entry_price,
                            'sl': sl,
                            'tp': tp,
                            'size': size
                        }
                        logger.info(f"Open {signal} at {entry_price:.2f} (Risk: ${risk_amount:.2f}, Cost: ${trade_cost:.2f})")
                    else:
                        # Log and Count the Skip
                        self.skipped_trades += 1
                        logger.warning(f"SKIPPED {signal}: Insufficient Capital. Need ${trade_cost:.2f}, Have ${self.capital:.2f}")

        # After loop ends, calculate stats
        self.calculate_metrics()
        self.save_log()

    def close_trade(self, exit_time, reason, exit_price):
        trade = self.position
        
        # Calculate PnL
        if trade['type'] == 'BUY':
            pnl = (exit_price - trade['entry']) * trade['size']
        else:
            pnl = (trade['entry'] - exit_price) * trade['size']

        self.capital += pnl

        record = {
            'timestamp': trade['entry_time'], 
            'symbol': trade['symbol'],
            'direction': trade['type'],
            'entry_price': trade['entry'],
            'exit_price': exit_price,
            'exit_time': exit_time,
            'pnl': pnl, # Keep float precision for calculation
            'capital_after': self.capital,
            'reason': reason
        }
        self.trades.append(record)
        logger.info(f"Closed {trade['type']} ({reason}) PnL: {pnl:.2f}")
        
        self.position = None 

    def calculate_metrics(self):
        """Calculates Sharpe and Sortino Ratios based on Daily Returns"""
        if not self.trades:
            logger.warning("No trades to calculate metrics.")
            return

        df_trades = pd.DataFrame(self.trades)
        
        # 1. Create a Daily Equity Curve
        daily_pnl = pd.Series(0, index=self.data.index)
        trade_pnl_by_date = df_trades.set_index('exit_time')['pnl'].resample('D').sum()
        daily_pnl = daily_pnl.resample('D').sum().add(trade_pnl_by_date, fill_value=0)
        equity_curve = self.initial_capital + daily_pnl.cumsum()
        
        # 2. Calculate Daily % Returns
        daily_returns = equity_curve.pct_change().dropna()
        
        # 3. Calculate Ratios
        ANNUAL_FACTOR = 365
        mean_return = daily_returns.mean() * ANNUAL_FACTOR
        std_dev = daily_returns.std() * np.sqrt(ANNUAL_FACTOR)
        
        sharpe_ratio = mean_return / std_dev if std_dev != 0 else 0
        
        negative_returns = daily_returns[daily_returns < 0]
        downside_std = negative_returns.std() * np.sqrt(ANNUAL_FACTOR)
        sortino_ratio = mean_return / downside_std if downside_std != 0 else 0

        # Log Results
        logger.info("-" * 40)
        logger.info("BACKTEST PERFORMANCE METRICS")
        logger.info("-" * 40)
        logger.info(f"Total Trades:      {len(df_trades)}")
        logger.info(f"Skipped Trades:    {self.skipped_trades} (Insufficient Capital)")
        logger.info(f"Final Balance:     ${self.capital:.2f}")
        logger.info(f"Net Profit:        ${self.capital - self.initial_capital:.2f}")
        logger.info(f"Sharpe Ratio:      {sharpe_ratio:.2f}")
        logger.info(f"Sortino Ratio:     {sortino_ratio:.2f}")
        logger.info("-" * 40)

    def save_log(self):
        df_trades = pd.DataFrame(self.trades)
        if not df_trades.empty:
            cols = ['timestamp', 'symbol', 'direction', 'entry_price', 'exit_price', 'pnl', 'capital_after']
            df_trades['pnl'] = df_trades['pnl'].round(2)
            df_trades['capital_after'] = df_trades['capital_after'].round(2)
            
            df_trades[cols].to_csv(Config.BACKTEST_OUTPUT, index=False)
            logger.info(f"Saved trades to {Config.BACKTEST_OUTPUT}")
        else:
            logger.warning("No trades generated.")

def run_custom_backtest():
    try:
        df_5m = pd.read_csv(Config.CSV_5M, parse_dates=True, index_col='timestamp')
        df_1h = pd.read_csv(Config.CSV_1H, parse_dates=True, index_col='timestamp')
    except FileNotFoundError:
        logger.error("Data files not found.")
        return

    data = calculate_indicators(df_5m, df_1h)
    data = data.dropna()

    engine = CustomBacktester(data, initial_capital=10000)
    engine.run()

if __name__ == "__main__":
    run_custom_backtest()