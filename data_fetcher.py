import pandas as pd
import requests
import time

def fetch_binance_data(symbol="BTCUSDT", interval ='1H' , days=365*2):
    base_url = "https://api.binance.com/api/v3/klines"
    end_time = int(time.time() * 1000)  # Current time in milliseconds
    start_time = end_time - (days * 24 * 60 * 60 * 1000)  # pass parameters AS per need

    all_data = []
    limit = 1000  # Binance API max limit per request 

    while start_time < end_time:
        url = f"{base_url}?symbol={symbol}&interval={interval}&limit={limit}&startTime={start_time}"
        response = requests.get(url)
        data = response.json()

        if not data:
            break  # When no more data available

        all_data.extend(data)
        start_time = data[-1][0] + 1  # Moving to the next 1000 units of data

        print(f"Fetched {len(all_data)} records so far...")

    df = pd.DataFrame(all_data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume", "ignore"
    ])

    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df[["open", "high", "low", "close","volume"]] = df[["open", "high", "low", "close","volume"]].astype(float)

    filename = f"{symbol}_{interval}_{days}.csv"
    df.to_csv(filename, index=False)
    print(f"Data saved as {filename}")

    return df

# Fetch 1-year BTC/USDT data (1m timeframe)
df = fetch_binance_data(symbol="BTCUSDT", interval="1h", days= 1000) #pass final parameters.
print(df.head())
