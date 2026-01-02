
# === Importa funzione get_all_tickers da my_tickers.py ===

from my_tickers import get_all_tickers
 
import pandas as pd
import yfinance as yf
import numpy as np
import warnings
from datetime import datetime
import os
import argparse
 
warnings.simplefilter('ignore', category=FutureWarning)
 
# === Argparse ===
parser = argparse.ArgumentParser(description="POC all tickers")
parser.add_argument("--poc_period", type=int, required=True, help="Periodo POC in anni (es. 5 = 5y)")
parser.add_argument("--soglia_poc", type=int, required=True, help="Soglia distanza POC in percentuale")
args = parser.parse_args()

# === Parametri principali ===
poc_period = f"{args.poc_period}y"   # ← conversione automatica in formato yfinance
soglia_poc = args.soglia_poc
filter_start_date = pd.to_datetime("2000-01-01")

 
# === Funzioni storiche ===
def get_hist(ticker, period):
    try:
        df = yf.download(ticker, period=period, progress=False)
        return df
    except Exception as e:
        print(f"Errore storico {ticker}: {e}")
        return pd.DataFrame()
 
def calculate_drawdowns(prices):
    if prices.empty:
        return np.nan, np.nan, np.nan
    cummax = prices.cummax()
    drawdown = (cummax - prices) / cummax * 100
    return drawdown.max(), drawdown.mean(), drawdown.iloc[-1]
 
def get_poc_daily(ticker, period="5y", bins=200):
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=False)
        if df.empty:
            return None
    except Exception as e:
        print(f"Errore download POC data for {ticker}: {e}")
        return None
 
    # Ensure column names are simple (not MultiIndex)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join(map(str, col)).strip() for col in df.columns]
 
    # Map to standard column names if necessary (case-insensitive)
    col_map = {}
    for col in df.columns:
        if 'high' in col.lower():
            col_map[col] = 'High'
        elif 'low' in col.lower():
            col_map[col] = 'Low'
        elif 'volume' in col.lower():
            col_map[col] = 'Volume'
    df = df.rename(columns=col_map)
 
    # Check for required columns after renaming
    if 'High' not in df.columns or 'Low' not in df.columns or 'Volume' not in df.columns:
        print(f"Missing required columns (High, Low, Volume) for POC calculation on {ticker}")
        return None
 
 
    price_min = df["Low"].min()
    price_max = df["High"].max()
    if price_min == price_max:
        return None
 
    price_bins = np.linspace(price_min, price_max, bins)
    volume_profile = np.zeros(len(price_bins) - 1)
 
    for _, row in df.iterrows():
        if row["High"] > row["Low"] and row["Volume"] > 0:
             # Find the indices of the bins covered by the High-Low range
            low_bin_idx = np.searchsorted(price_bins, row["Low"], side='right') - 1
            high_bin_idx = np.searchsorted(price_bins, row["High"], side='left')
 
            # Ensure indices are valid and low <= high
            low_bin_idx = max(0, min(low_bin_idx, len(price_bins) - 2))
            high_bin_idx = max(0, min(high_bin_idx, len(price_bins) - 1))
 
 
            if high_bin_idx > low_bin_idx:
                bins_covered = np.arange(low_bin_idx, high_bin_idx)
                if len(bins_covered) > 0:
                    vol_share = row["Volume"] / len(bins_covered)
                    volume_profile[bins_covered] += vol_share
            elif high_bin_idx == low_bin_idx and low_bin_idx < len(price_bins) -1: # Handle case where High and Low fall in the same bin
                 volume_profile[low_bin_idx] += row["Volume"] # Add all volume to that bin
 
 
    if volume_profile.sum() == 0:
        return None
 
    poc_index = np.argmax(volume_profile)
    # Ensure poc_index is a valid index for price_bins
    if poc_index >= len(price_bins) -1:
        poc_index = len(price_bins) - 2 # Fallback to the last valid bin midpoint
 
 
    poc_price = (price_bins[poc_index] + price_bins[poc_index + 1]) / 2
    return poc_price
 
 
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
 
# === Ciclo principale sui ticker ===
risultati = []
 
for ticker in all_tickers:
    try:
        poc_price = get_poc_daily(ticker, period=poc_period)
        if poc_price is None:
            continue
 
        df_hist = get_hist(ticker, period="1d")
        if df_hist.empty or "Close" not in df_hist.columns:
            continue
        current_price = float(df_hist["Close"].iloc[-1])
 
        distanza_poc = (current_price - poc_price) / poc_price * 100
 
        if abs(distanza_poc) <= soglia_poc:
            df_all = get_hist(ticker, period="max")
            if df_all.empty or "Close" not in df_all.columns:
                continue
            df_filtered = df_all[df_all.index >= filter_start_date].copy()
            if df_filtered.empty:
                continue
 
            close_prices = df_filtered["Close"]
            all_time_high = close_prices.max()
            max_dd, avg_dd, current_dd = calculate_drawdowns(close_prices)
 
            risultati.append({
                "Ticker": ticker,
                "Indice": ticker_to_index[ticker],
                "POC": poc_price,
                "Prezzo Attuale": current_price,
                "Distanza POC %": distanza_poc,
                "All Time High": float(all_time_high),
                "Max Drawdown %": float(max_dd),
                "Avg Drawdown %": float(avg_dd),
                "Current Drawdown %": float(current_dd)
            })
 
    except Exception as e:
        print(f"Errore con {ticker}: {e}")
        continue
 
# === Risultati ===
df_risultati = pd.DataFrame(risultati)
 
if df_risultati.empty:
    print("⚠ Nessun titolo ha passato i filtri sulla distanza dal POC o non ha dati storici sufficienti.")
else:
    df_risultati = df_risultati.sort_values(by="Current Drawdown %", ascending=False)
 
    # Stampare l'intero DataFrame come testo
    print(df_risultati.to_string())
 
  
# === Salvataggio file Excel (sovrascrivibile nella stessa settimana) ===
week_number = datetime.now().isocalendar()[1]

BASE = os.path.dirname(os.path.abspath(__file__))  # = data/
OUTPUT_DIR = os.path.join(BASE, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

file_name = f"POC_p{poc_period}_s{soglia_poc}_week_{week_number}.xlsx"
file_path = os.path.join(OUTPUT_DIR, file_name)

df_risultati.to_excel(file_path, index=False)

print(f"\n✅ File salvato (sovrascritto se esiste): {file_path}")
 

