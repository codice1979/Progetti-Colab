import os
import sys
import pandas as pd
import yfinance as yf
import numpy as np

# =========================
# Importa get_all_tickers
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from my_tickers import get_all_tickers

print("✅ Funzione get_all_tickers importata correttamente.")

# =========================
# FUNZIONI POC ORARIO (240 barre)
# =========================

def get_poc_from_df(df, bins=200):
    if df is None or df.empty:
        return None

    # Normalizza colonne (gestione MultiIndex yfinance)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join(col).strip() for col in df.columns]

    df = df.rename(columns={
        c: "High" for c in df.columns if "high" in c.lower()
    } | {
        c: "Low" for c in df.columns if "low" in c.lower()
    } | {
        c: "Volume" for c in df.columns if "volume" in c.lower()
    })

    if not {"High", "Low", "Volume"}.issubset(df.columns):
        return None

    price_min = df["Low"].min()
    price_max = df["High"].max()
    if price_min == price_max:
        return None

    price_bins = np.linspace(price_min, price_max, bins)
    volume_profile = np.zeros(len(price_bins) - 1)

    for _, row in df.iterrows():
        if row["High"] > row["Low"] and row["Volume"] > 0:
            low_idx = np.searchsorted(price_bins, row["Low"], side="right") - 1
            high_idx = np.searchsorted(price_bins, row["High"], side="left")

            low_idx = max(0, min(low_idx, len(price_bins) - 2))
            high_idx = max(0, min(high_idx, len(price_bins) - 1))

            if high_idx > low_idx:
                vol_share = row["Volume"] / (high_idx - low_idx)
                volume_profile[low_idx:high_idx] += vol_share
            else:
                volume_profile[low_idx] += row["Volume"]

    if volume_profile.sum() == 0:
        return None

    i = np.argmax(volume_profile)
    return (price_bins[i] + price_bins[i + 1]) / 2


def get_poc_hourly_240(ticker):
    try:
        df = yf.download(
            ticker,
            period="60d",
            interval="1h",
            progress=False,
            auto_adjust=False
        )

        if df.empty:
            return None

        df = df.tail(240)
        return get_poc_from_df(df)

    except Exception as e:
        print(f"⚠ POC error {ticker}: {e}")
        return None


# =========================
# Costruzione mappa ticker → indici
# =========================

ticker_dict = get_all_tickers(flat=False)

ticker_to_index = {}

for index_name, tickers in ticker_dict.items():
    for ticker in tickers:
        if ticker in ticker_to_index:
            ticker_to_index[ticker].add(index_name)
        else:
            ticker_to_index[ticker] = {index_name}

all_tickers = sorted(ticker_to_index.keys())
print(f"🔍 Trovati {len(all_tickers)} ticker unici")

# =========================
# Recupero dati
# =========================

rows = []

for ticker in all_tickers:
    try:
        t = yf.Ticker(ticker)
        info = t.info

        name = info.get("longName") or info.get("shortName") or ""
        sector = info.get("sector") or ""

        market_cap = info.get("marketCap")
        market_cap_b = round(market_cap / 1_000_000_000, 3) if market_cap else None

        # ✅ PREZZO ATTUALE
        price = info.get("currentPrice")
        if price is None:
            df_last = yf.download(ticker, period="1d", progress=False)
            if not df_last.empty:
                price = float(df_last["Close"].iloc[-1])

        # ✅ POC ORARIO
        poc_h_240 = get_poc_hourly_240(ticker)

        index_str = ", ".join(sorted(ticker_to_index[ticker]))

        rows.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "index": index_str,
            "market_cap_B": market_cap_b,
            "price": price,
            "poc_h_240": poc_h_240
        })

        print(f"✅ {ticker} → price={price}, poc_h_240={poc_h_240}")

    except Exception as e:
        print(f"❌ Errore su {ticker}: {e}")
        rows.append({
            "ticker": ticker,
            "name": "",
            "sector": "",
            "index": ", ".join(sorted(ticker_to_index[ticker])),
            "market_cap_B": None,
            "price": None,
            "poc_h_240": None
        })

# =========================
# Salvataggio Excel
# =========================

df = pd.DataFrame(
    rows,
    columns=["ticker", "name", "sector", "index", "market_cap_B", "price", "poc_h_240"]
)

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

output_file = os.path.join(OUTPUT_DIR, "tickers_info.xlsx")
df.to_excel(output_file, index=False)

print(f"\n📊 File creato: {output_file}")
