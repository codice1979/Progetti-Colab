# --------------------------
# KEY REVERSAL WEEKLY / GITHUB ACTIONS
# --------------------------

# !pip install ta  # Rimuovi "!" in Actions, installa via workflow
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import ta

# === Importa funzione get_all_tickers da my_tickers.py ===
import sys
import os

# Assumiamo che my_tickers.py sia nella stessa cartella dello script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from my_tickers import get_all_tickers

# =========================
# Recupera tutti i ticker con indice
# =========================
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

# =========================
# Funzione analyze_key_reversal
# =========================
def analyze_key_reversal(tickers):
    lookback = 2
    rsi_period = 9
    cutoff_date = datetime.today() - timedelta(days=30)
    results = []

    for ticker in tickers:
        try:
            df = yf.download(
                ticker,
                period="2y",
                interval="1wk",
                progress=False,
                group_by='ticker',
                auto_adjust=False
            )
            if df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(1)
            elif any(ticker in col for col in df.columns):
                df.columns = [col.split('.')[-1] for col in df.columns]

            df.index = pd.to_datetime(df.index)
            df["RSI"] = ta.momentum.RSIIndicator(close=df["Close"], window=rsi_period).rsi()
            df["Close_1"] = df["Close"].shift(1)
            df["Low_1n"] = df["Low"].shift(1).rolling(lookback).min()
            df["High_1n"] = df["High"].shift(1).rolling(lookback).max()

            df["KR_Up"] = (df["Low"] < df["Low_1n"]) & (df["Close"] > df["Close_1"]) & (df["RSI"] < 30)
            df["KR_Down"] = (df["High"] > df["High_1n"]) & (df["Close"] < df["Close_1"]) & (df["RSI"] > 70)

            signals = df[(df["KR_Up"]) | (df["KR_Down"])].copy()
            signals = signals[signals.index >= cutoff_date]

            for date, row in signals.iterrows():
                results.append({
                    "Ticker": ticker,
                    "Date": (pd.to_datetime(date) + timedelta(days=4)).strftime("%Y-%m-%d"),
                    "Signal": "Rialzista" if row["KR_Up"] else "Ribassista"
                })

        except Exception as e:
            # stampa eventuali errori
            print(f"Errore su {ticker}: {e}")

    df_out = pd.DataFrame(results)
    if not df_out.empty:
        print(df_out[["Ticker", "Date", "Signal"]])
    else:
        print("No signals found within the specified date range.")

    return df_out

# =========================
# Esecuzione principale
# =========================
if __name__ == "__main__":
    all_tickers = get_all_tickers()
    df_results = analyze_key_reversal(all_tickers)

    # Salva il risultato come XLSX nella cartella output
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, "key_reversal_signals_week_{week_number}.xlsx")
    df_results.to_excel(output_file, index=False)
    print(f"✅ File salvato: {output_file}")
