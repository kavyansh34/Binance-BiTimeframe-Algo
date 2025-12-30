# configuration.py
class Config:
    # Exchange Settings
    SYMBOL = 'BTCUSDT' # bitcoin perpetual contract
    TESTNET_BASE_URL = "https://testnet.binance.vision"
    
    # API KEYS (Replace with your Testnet Keys)
    API_KEY = 'YOUR API KEY'
    API_SECRET = 'YOUR API SECRET'

    # Timeframes
    TF_ENTRY = '5m'  # Entry timeframe
    TF_FILTER = '1h'  # Filter timeframe

    # Strategy Params
    EMA_PERIOD = 21
    RISK_PER_TRADE = 0.001  # 0.01% of capital
    RR_RATIO = 1.5         # Reward to Risk 1:1.5
    
    # File Paths
    CSV_5M = 'BTCUSDT_5m_1000.csv' # User provided CSV path
    CSV_1H = 'BTCUSDT_1h_1000.csv'   # User provided CSV path
    BACKTEST_OUTPUT = 'backtest_trades.csv' # To store trades while backtesting
    LIVE_OUTPUT = 'live_trades.csv' # To store live trades
