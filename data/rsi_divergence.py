# ✅ Installazione librerie già gestita da workflow GitHub, quindi !pip non serve

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import yfinance as yf
import pandas as pd
from bs4 import BeautifulSoup
import requests
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# ✅ Helper per scalari da array
def scalar(x):
    return float(np.asarray(x).item())

# ✅ Calcolo RSI in stile TradingView (RMA)
def compute_rsi_rma(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ✅ Importa funzione get_all_tickers dal repo (cartella data)
sys.path.append('./data')
from my_tickers import get_all_tickers
print("✅ Funzione get_all_tickers importata correttamente.")

# === Recupera tutti i ticker con indice ===
ticker_dict = get_all_tickers(flat=False)
ticker_to_index = {}
for idx_name, tickers in ticker_dict.items():
    for t in tickers:
        if t in ticker_to_index:
            ticker_to_index[t] += f", {idx_name}"
        else:
            ticker_to_index[t] = idx_name

all_tickers = list(ticker_to_index.keys())
print(f"Trovati {len(all_tickers)} ticker tra tutti gli indici")

# ✅ Scarica dati settimanali e calcola RSI
def fetch_weekly_data(ticker):
    if not ticker or not isinstance(ticker, str):
        print(f"❌ Errore: Ticker vuoto o non valido ('{ticker}').")
        return None
    try:
        df = yf.download(ticker, period="1y", interval="1wk", auto_adjust=False, progress=False)
        if df.empty or "Close" not in df.columns:
            return None
        df["RSI"] = compute_rsi_rma(df["Close"])
        df = df[["Close", "RSI"]].dropna()
        df.name = ticker
        return df
    except Exception as e:
        print(f"❌ Errore su {ticker}: {e}")
        return None

# ✅ Trova swing points
def find_pivots(series, window=2):
    pivots = []
    values = series.values
    index = series.index
    for i in range(window, len(series) - window):
        left = values[i - window:i]
        right = values[i + 1:i + 1 + window]
        center = values[i]
        if all(center > val for val in left) and all(center > val for val in right):
            pivots.append((index[i], center, 'max'))
        elif all(center < val for val in left) and all(center < val for val in right):
            pivots.append((index[i], center, 'min'))
    return pivots

# ✅ Divergenze RSI
def detect_divergence_with_values(df, mode="bullish", window=2, max_days=42, max_days_from_now=30):
    if df is None or len(df) < (2 * window + 1):
        return None

    df = df.copy()
    pivots_price = find_pivots(df['Close'], window=window)
    pivots_rsi   = find_pivots(df['RSI'], window=window)

    tipo = 'min' if mode == 'bullish' else 'max'
    price_pivots = [(d, v) for (d, v, k) in pivots_price if k == tipo]
    rsi_pivots   = [(d, v) for (d, v, k) in pivots_rsi if k == tipo]

    price_dict = dict(price_pivots)
    rsi_dict = dict(rsi_pivots)

    common_dates = sorted(set(price_dict.keys()) & set(rsi_dict.keys()))
    if len(common_dates) < 2:
        return None

    d1, d2 = common_dates[-2], common_dates[-1]
    p1, p2 = price_dict[d1], price_dict[d2]
    r1, r2 = rsi_dict[d1], rsi_dict[d2]

    if (d2 - d1).days > max_days:
        return None
    if (datetime.now() - d2).days > max_days_from_now:
        return None

    if mode == 'bullish' and (p2 < p1) and (r2 > r1) and (min(r1, r2) < 35):
        return {"date1": d1, "date2": d2, "price1": p1, "price2": p2, "rsi1": r1, "rsi2": r2}
    if mode == 'bearish' and (p2 > p1) and (r2 < r1) and (max(r1, r2) > 65):
        return {"date1": d1, "date2": d2, "price1": p1, "price2": p2, "rsi1": r1, "rsi2": r2}

    return None

# ✅ Analisi generale
results = []
print(f"🔍 Analisi di {len(all_tickers)} ticker...\n")

for ticker in all_tickers:
    df = fetch_weekly_data(ticker)
    if df is None:
        continue

    bull = detect_divergence_with_values(df, "bullish")
    bear = detect_divergence_with_values(df, "bearish")

    if bull:
        results.append({
            "Ticker": ticker,
            "Mode": "bullish",
            "Date1": bull["date1"].date(),
            "Price1": round(scalar(bull["price1"]), 2),
            "RSI1": round(bull["rsi1"], 2),
            "Date2": bull["date2"].date(),
            "Price2": round(scalar(bull["price2"]), 2),
            "RSI2": round(bull["rsi2"], 2),
        })
        print(f"✅ Divergenza rialzista su: {ticker}")

    if bear:
        results.append({
            "Ticker": ticker,
            "Mode": "bearish",
            "Date1": bear["date1"].date(),
            "Price1": round(scalar(bear["price1"]), 2),
            "RSI1": round(bear["rsi1"], 2),
            "Date2": bear["date2"].date(),
            "Price2": round(scalar(bear["price2"]), 2),
            "RSI2": round(bear["rsi2"], 2),
        })
        print(f"✅ Divergenza ribassista su: {ticker}")

# ✅ Output tabella finale
print("\n📊 Riepilogo divergenze recenti:")
if results:
    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))
    # Salvataggio in data/output/
    os.makedirs("data/output", exist_ok=True)
    output_file = os.path.join("data/output", f"rsi_divergences_week_{week_number}.xlsx")
    df_res.to_excel(output_file, index=False)
    print(f"\n✅ File salvato: {output_file}")
else:
    print("🚫 Nessuna divergenza recente trovata.")
