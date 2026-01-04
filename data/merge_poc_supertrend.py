import os
import argparse
from datetime import datetime
import pandas as pd
import yfinance as yf
import numpy as np
import talib as ta

# =========================
# PATH LOCALI
# =========================
BASE_DIR = "./data"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# ARGOMENTI CLI
# =========================
parser = argparse.ArgumentParser()
parser.add_argument("--poc_period", required=True)
parser.add_argument("--soglia_poc", required=True)
args = parser.parse_args()

poc_period = args.poc_period
soglia_poc = args.soglia_poc
week_number = datetime.now().isocalendar()[1]

# =========================
# FILE INPUT POC
# =========================
poc_file_path = os.path.join(
    OUTPUT_DIR,
    f"POC_p{poc_period}_s{soglia_poc}_week_{week_number}.xlsx"
)

print("📂 Carico:", poc_file_path)

if not os.path.exists(poc_file_path):
    raise FileNotFoundError(f"❌ File POC non trovato: {poc_file_path}")

df_poc = pd.read_excel(poc_file_path)
print("📊 Colonne POC:", list(df_poc.columns))

# =========================
# TROVA COLONNA TICKER
# =========================
possible_ticker_cols = ["Ticker", "ticker", "TICKER", "Symbol", "SYMBOL"]
ticker_col = next((c for c in possible_ticker_cols if c in df_poc.columns), None)

if ticker_col is None:
    raise KeyError("❌ Colonna ticker non trovata nel file POC")

print(f"✅ Colonna ticker usata: {ticker_col}")

# =========================
# FUNZIONI SUPERTREND (TA-Lib + Delta %)
# =========================
def clean_df(df):
    """Pulizia dataframe yfinance"""
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    for col in ['High','Low','Close']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['High','Low','Close'])
    return df

def calculate_supertrend(high, low, close, atr_period=10, multiplier=3.0):
    """Calcola ultimo valore SuperTrend in stile TradingView usando TA-Lib"""
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)

    if len(close) < atr_period:
        return np.nan

    atr = ta.ATR(high, low, close, timeperiod=atr_period)
    upperband = (high + low)/2 + multiplier*atr
    lowerband = (high + low)/2 - multiplier*atr

    supertrend = np.full_like(close, np.nan)
    direction = np.full_like(close, np.nan)

    first_valid_idx = np.where(~np.isnan(atr))[0][0]
    supertrend[first_valid_idx] = upperband[first_valid_idx]
    direction[first_valid_idx] = 1

    for i in range(first_valid_idx+1, len(close)):
        prev_st = supertrend[i-1]
        if close[i] > prev_st:
            direction[i] = 1
        else:
            direction[i] = -1
        supertrend[i] = max(lowerband[i], prev_st) if direction[i]==1 else min(upperband[i], prev_st)

    supertrend[:first_valid_idx] = supertrend[first_valid_idx]
    return supertrend[-1]

def st_distance_pct(df):
    """Calcola delta % tra prezzo di chiusura e ST ultimo punto"""
    df = clean_df(df)
    if df.empty or len(df) < 20:
        return np.nan
    st_last = calculate_supertrend(df['High'], df['Low'], df['Close'])
    if np.isnan(st_last):
        return np.nan
    close_last = float(df['Close'].iloc[-1])
    return round((close_last - st_last)/st_last * 100, 1)

# =========================
# CALCOLO ST MULTI-TIMEFRAME
# =========================
rows = []

tickers = (
    df_poc[ticker_col]
    .dropna()
    .astype(str)
    .unique()
)

for ticker in tickers:
    try:
        df_4h = yf.download(ticker, period="60d", interval="4h", progress=False, auto_adjust=True)
        df_d = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        df_w = yf.download(ticker, period="1y", interval="1wk", progress=False, auto_adjust=True)
        df_m = yf.download(ticker, period="2y", interval="1mo", progress=False, auto_adjust=True)

        rows.append({
            ticker_col: ticker,
            "ST_4H_Delta%": st_distance_pct(df_4h),
            "ST_Daily_Delta%": st_distance_pct(df_d),
            "ST_Weekly_Delta%": st_distance_pct(df_w),
            "ST_Monthly_Delta%": st_distance_pct(df_m),
        })

    except Exception as e:
        print(f"⚠️ Errore su {ticker}: {e}")

df_st = pd.DataFrame(rows)

# =========================
# MERGE
# =========================
df_final = df_poc.merge(df_st, on=ticker_col, how="left")

# =========================
# EXPORT
# =========================
output_file_path = os.path.join(
    OUTPUT_DIR,
    f"POC_ST_p{poc_period}_s{soglia_poc}_week_{week_number}.xlsx"
)

df_final.to_excel(output_file_path, index=False)

print(f"\n✅ File POC + SuperTrend creato con successo:\n{output_file_path}")
