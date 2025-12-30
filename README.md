# Binance-BiTimeframe-Algo 🚀

**Binance-BiTimeframe-Algo** is a systematic algorithmic trading engine designed for the **Binance Spot Market**. It features a hybrid execution model with dual-timeframe trend analysis (1H Trend + 5M Entry) and institutional-grade risk management.

## ⚡ Key Features
* **Dual Timeframe Analysis:** Filters trades based on 1H trends (EMA 21) while executing entries on 5M candles.
* **Spot-Safe Execution:** Automatically filters out Short (Sell) signals to prevent execution errors in Spot markets.
* **Smart Capital Protection:** "Skip Trade" logic prevents execution if the account balance is insufficient for the calculated position size.
* **Event-Driven Backtester:** Custom backtesting engine with accurate Sharpe/Sortino ratio calculations and trade logging.
* **Live Logging:** Detailed console logs for every signal, trend check, and order execution.

## 🛠️ Installation
1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/kavyansh34/Binance-BiTimeframe-Algo](https://github.com/kavyansh34/Binance-BiTimeframe-Algo.git)
    cd Binance-BiTimeframe-Algo
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration:**
    * Rename `configuration_template.py` to `configuration.py`.
    * Open `configuration.py` and paste your Binance API Keys (Testnet or Mainnet).

## 📈 Usage

**Run Live Trading (Spot Testnet):**
```bash
python live_runner.py
```

**Run backtest window :**
```bash
python backtest_runner.py
```

**sample trades** are provided in 'Screenshot 2025-12-30 181028.png' file
