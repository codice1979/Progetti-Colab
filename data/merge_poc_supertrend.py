import os
import argparse
from datetime import datetime

import pandas as pd
import numpy as np
import yfinance as yf

# =========================
# PATH LOCALI (GitHub Actions / locale)
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

# =========================
# SETTIMANA CORRENTE
# =========================
week_number = datetime.now().isocalendar()[1]

# =========================
# FILE INPUT POC
# =========================
poc_file_path = os.path.join(
    OUTPUT_DIR,
    f"POC_p{poc_period}_s{soglia_poc}_week_{week_number}.xlsx"
)

print("📂 Cerco file POC in:")
print(poc_file_path)

if not os.path.exists(poc_file_path):
    raise FileNotFoundError(f"❌ File POC non trovato: {poc_file_path}")

# =========================
# CARICAMENTO POC
# =========================
df_poc = pd.read_excel(poc_file_path)

# =========================
# FUNZIONE SUPERTREND
# =========================
def supertrend(df, period=10, multiplier=3):
    hl2 = (df["High"] + df["Low"]) / 2
    atr = df["High"].rolling(period).max() - df["Low"].rolling(period).min()

    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    trend = [True]
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > upperband.iloc[i - 1]:
            trend.append(True)
        elif df["Close"].iloc[i] < lowerband.iloc[i - 1]:
            trend.append(False)
        else:
            trend.append(trend[i - 1])

    df["SuperTrend"] = trend
    return df

# =========================
# DOWNLOAD DATI + SUPERTREND
# =========================
results = []

for ticker in df_poc["Ticker"].unique():
    try:
        data = yf.download(ticker, period="2y", interval="1wk", progress=False)

        if data.empty:
            continue

        data = data.reset_index()
        data = supertrend(data)

        last_row = data.iloc[-1]

        results.append({
            "Ticker": ticker,
            "SuperTrend": "UP" if last_row["SuperTrend"] else "DOWN"
        })

    except Exception as e:
        print(f"⚠️ Errore su {ticker}: {e}")

df_st = pd.DataFrame(results)

# =========================
# MERGE POC + SUPERTREND
# =========================
df_final = df_poc.merge(df_st, on="Ticker", how="left")

# =========================
# EXPORT FINALE
# =========================
output_file_path = os.path.join(
    OUTPUT_DIR,
    f"POC_ST_p{poc_period}_s{soglia_poc}_week_{week_number}.xlsx"
)

df_final.to_excel(output_file_path, index=False)

print(f"✅ File POC + SuperTrend esportato in:\n{output_file_path}")
