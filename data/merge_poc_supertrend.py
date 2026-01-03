import os
import argparse
from datetime import datetime
import pandas as pd
import yfinance as yf

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
df_poc = pd.read_excel(poc_file_path)

print("📊 Colonne POC:", list(df_poc.columns))

# =========================
# TROVA COLONNA TICKER
# =========================
possible_ticker_cols = ["Ticker", "ticker", "TICKER", "Symbol", "SYMBOL"]

ticker_col = next((c for c in possible_ticker_cols if c in df_poc.columns), None)

if ticker_col is None:
    raise KeyError("❌ Colonna ticker non trovata nel POC")

print(f"✅ Colonna ticker usata: {ticker_col}")

# =========================
# SUPERTREND (LOGICA SEMPLICE, SCALARE)
# =========================
def supertrend_last(df, period=10, multiplier=3):
    hl2 = (df["High"] + df["Low"]) / 2
    atr = (df["High"] - df["Low"]).rolling(period).mean()

    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr

    trend = True
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > upperband.iloc[i - 1]:
            trend = True
        elif df["Close"].iloc[i] < lowerband.iloc[i - 1]:
            trend = False

    return bool(trend)

# =========================
# CALCOLO SUPERTREND
# =========================
results = []

for ticker in df_poc[ticker_col].dropna().unique():
    try:
        data = yf.download(
            ticker,
            period="2y",
            interval="1wk",
            progress=False
        )

        if data.empty or len(data) < 20:
            continue

        st_up = supertrend_last(data)

        results.append({
            ticker_col: ticker,
            "ST_Weekly": "UP" if st_up else "DOWN"
        })

    except Exception as e:
        print(f"⚠️ Errore su {ticker}: {e}")

df_st = pd.DataFrame(results)

# =========================
# MERGE CORRETTO
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

print(f"✅ File creato:\n{output_file_path}")
