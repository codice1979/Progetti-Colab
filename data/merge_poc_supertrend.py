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
# PARAMETRI SUPERTREND (TV)
# =========================
ATR_PERIOD = 10
MULTIPLIER = 3.0

# =========================
# FUNZIONI SUPERTREND TV-ALIGNED
# =========================
def clean_df(df):
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    for col in ["High", "Low", "Close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["High", "Low", "Close"])

def calculate_atr(high, low, close, period):
    high, low, close = map(np.asarray, (high, low, close))

    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(
            np.abs(high[1:] - close[:-1]),
            np.abs(low[1:] - close[:-1])
        )
    )

    atr = np.full(len(close), np.nan)
    atr[period] = tr[:period].mean()

    for i in range(period + 1, len(close)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i - 1]) / period

    return atr

def supertrend_tv(high, low, close, period, multiplier):
    atr = calculate_atr(high, low, close, period)
    if np.all(np.isnan(atr)):
        return np.full(len(close), np.nan)

    hl2 = (high + low) / 2
    upper_basic = hl2 + multiplier * atr
    lower_basic = hl2 - multiplier * atr

    upper_final = np.copy(upper_basic)
    lower_final = np.copy(lower_basic)
    st = np.full(len(close), np.nan)
    direction = np.ones(len(close))

    first = np.where(~np.isnan(atr))[0][0]
    st[first] = lower_final[first]

    for i in range(first + 1, len(close)):
        upper_final[i] = (
            min(upper_basic[i], upper_final[i - 1])
            if close[i - 1] <= upper_final[i - 1]
            else upper_basic[i]
        )
        lower_final[i] = (
            max(lower_basic[i], lower_final[i - 1])
            if close[i - 1] >= lower_final[i - 1]
            else lower_basic[i]
        )

        if close[i] > upper_final[i - 1]:
            direction[i] = 1
        elif close[i] < lower_final[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]

        st[i] = lower_final[i] if direction[i] == 1 else upper_final[i]

    st[:first] = st[first]
    return st

def compute_st_and_delta(df):
    df = clean_df(df)
    if len(df) < ATR_PERIOD * 3:
        return np.nan, np.nan, np.nan

    st = supertrend_tv(
        df["High"].values,
        df["Low"].values,
        df["Close"].values,
        ATR_PERIOD,
        MULTIPLIER
    )

    st_last = float(st[-1])
    close_last = float(df["Close"].iloc[-1])

    if st_last <= 0:
        return np.nan, close_last, np.nan

    delta = (close_last - st_last) / st_last * 100
    return st_last, close_last, delta

# =========================
# CALCOLO ST MULTI-TIMEFRAME (TV)
# =========================
rows = []

tickers = df_poc[ticker_col].dropna().astype(str).unique()

for ticker in tickers:
    try:
        df_4h = yf.download(ticker, period="120d", interval="4h", auto_adjust=False, progress=False)
        df_d  = yf.download(ticker, period="1y",   interval="1d", auto_adjust=False, progress=False)
        df_w  = yf.download(ticker, period="5y",   interval="1wk", auto_adjust=False, progress=False)
        df_m  = yf.download(ticker, period="10y",  interval="1mo", auto_adjust=False, progress=False)

        _, _, delta_4h = compute_st_and_delta(df_4h)
        _, _, delta_d  = compute_st_and_delta(df_d)
        _, _, delta_w  = compute_st_and_delta(df_w)
        _, _, delta_m  = compute_st_and_delta(df_m)

        rows.append({
            ticker_col: ticker,
            "ST_4H_Delta%": round(delta_4h, 2),
            "ST_Daily_Delta%": round(delta_d, 2),
            "ST_Weekly_Delta%": round(delta_w, 2),
            "ST_Monthly_Delta%": round(delta_m, 2),
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
