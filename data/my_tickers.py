import requests
import pandas as pd
from io import StringIO

def get_tickers_from_wiki(url, column_name, suffix="", manual_list=None):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        html = response.text
        tables = pd.read_html(StringIO(html))  # ✅ FIX CRITICO

        exceptions_no_suffix = ["MT.AS"]

        for table in tables:
            if column_name in table.columns:
                tickers = []
                for t in table[column_name].dropna().unique():
                    ticker = str(t).strip()

                    if ticker in ["BRK.B", "BF.B"]:
                        tickers.append(ticker.replace(".", "-"))
                        continue

                    ticker = ticker.replace("-", ".")

                    if ticker not in exceptions_no_suffix:
                        known_suffixes = [".DE", ".PA", ".MI"]
                        if suffix and not any(ticker.endswith(s) for s in known_suffixes):
                            ticker += suffix

                    tickers.append(ticker)

                if tickers:
                    return tickers

        # fallback
        if manual_list:
            print(f"⚠️ Nessuna tabella trovata su {url}, uso fallback manuale")
            return manual_list
        return []

    except Exception as e:
        print(f"❌ Errore caricamento da {url}: {e}")
        if manual_list:
            print("➡️ Uso lista manuale di fallback")
            return manual_list
        return []
