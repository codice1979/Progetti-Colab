import os
import sys
import pandas as pd
import yfinance as yf

# =========================
# Importa get_all_tickers
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from my_tickers import get_all_tickers

print("✅ Funzione get_all_tickers importata correttamente.")

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
# Recupero name, sector, market cap
# =========================
rows = []

for ticker in all_tickers:
    try:
        info = yf.Ticker(ticker).info

        name = info.get("longName") or info.get("shortName") or ""
        sector = info.get("sector") or ""

        market_cap = info.get("marketCap")
        market_cap_b = round(market_cap / 1_000_000_000, 3) if market_cap else None

        index_str = ", ".join(sorted(ticker_to_index[ticker]))

        rows.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "index": index_str,
            "market_cap_B": market_cap_b
        })

        print(f"✅ {ticker} → {index_str}")

    except Exception as e:
        print(f"❌ Errore su {ticker}: {e}")
        rows.append({
            "ticker": ticker,
            "name": "",
            "sector": "",
            "index": ", ".join(sorted(ticker_to_index[ticker])),
            "market_cap_B": None
        })

# =========================
# Salvataggio Excel
# =========================
df = pd.DataFrame(
    rows,
    columns=["ticker", "name", "sector", "index", "market_cap_B"]
)

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

output_file = os.path.join(OUTPUT_DIR, "tickers_info.xlsx")
df.to_excel(output_file, index=False)

print(f"\n📊 File creato: {output_file}")
