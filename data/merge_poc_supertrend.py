import os
import argparse
from datetime import datetime
import pandas as pd
import yfinance as yf
import numpy as np

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
# SUPERTREND (STILE TradingView)
# =========================
def supertrend_series(df, period=10, multiplier=3):
    """
    Ritorna array numpy con il valore del SuperTrend
    """
    if df.empty or len(df) < period:
        return np.array([np.nan])

    df = df.copy()
    # Normalizza colonne (yfinance MultiIndex)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    high = df["High"].astype(float).values
    low = df["Low"].astype(float).values
    close = df["Close"].astype(float).values

    hl2 = (high + low) / 2
    atr = pd.Series(high - low).rolling(period).mean().values

    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr

    st = np.full(len(close), np.nan)
    direction = 1

    for i in range(period, len(close)):
        if np.isnan(upperband[i - 1]) or np.isnan(lowerband[i - 1]):
            continue
        if close[i] > upperband[i - 1]:
            direction = 1
        elif close[i] < lowerband[i - 1]:
            direction = -1

        st[i] = lowerband[i] if direction == 1 else upperband[i]

    return st

def st_distance_pct(df):
    """
    Calcola il delta % tra prezzo di chiusura e ST dell'ultimo punto
    """
    if df.empty or len(df) < 20:
        return np.nan

    st = supertrend_series(df)
    if np.isnan(st[-1]):
        return np.nan

    close_val = float(df["Close"].iloc[-1])
    st_val = float(st[-1])
    return round((close_val - st_val) / st_val * 100, 1)

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
            "ST_4H": st_distance_pct(df_4h),
            "ST_Daily": st_distance_pct(df_d),
            "ST_Weekly": st_distance_pct(df_w),
            "ST_Monthly": st_distance_pct(df_m),
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
