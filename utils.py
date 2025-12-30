# utils.py
import pandas as pd
import pandas_ta as ta
import logging
import sys

def setup_logger(name, log_file='system.log'):
    """Sets up a logger to file and console """
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.addHandler(console)
    return logger

def calculate_indicators(df_5m, df_1h):
    """
    Calculates EMA on 1H data and merges it onto 5M data.
    Ensures 'Single Source of Truth' for data processing.
    """

    df_1h = df_1h.rename(columns= {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'})
    df_5m = df_5m.rename(columns= {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'})
    # Calculate EMA on 1H data
    df_1h['EMA_21'] = ta.ema(df_1h['Close'], length=21)
    
    # Rename columns to avoid collision during merge
    df_1h_renamed = df_1h[['Close', 'EMA_21']].rename(
        columns={'Close': 'Close_1h', 'EMA_21': 'EMA_21_1h'}
    )
    
    # Merge 1H data onto 5m data
    # We forward fill the 1H data to align with 5m timestamps
    # This simulates the "Wait until next 1hr candle closes" logic
    df_merged = df_5m.merge(df_1h_renamed, left_index=True, right_index=True, how='left')
    df_merged[['Close_1h', 'EMA_21_1h']] = df_merged[['Close_1h', 'EMA_21_1h']].ffill()
    
    return df_merged

def check_engulfing(open_curr, close_curr, open_prev, close_prev, direction):
    """
    Validates Engulfing Pattern strictly.
    """
    # print(f"last open: {open_curr},last closed: {close_curr},last to last open: {open_prev},last to last close: {close_prev}, {direction}")
    if direction == 'BULLISH':
        # Previous Red, Current Green
        if close_prev < open_prev and close_curr > open_curr:
            # Body Engulfs Body
            if close_curr > open_prev and open_curr <= close_prev:
                return True
    elif direction == 'BEARISH':
        # Previous Green, Current Red
        if close_prev > open_prev and close_curr < open_curr:
            # Body Engulfs Body
            if close_curr < open_prev and open_curr >= close_prev:
                return True
    return False