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
# SUPERTREND (ROBUSTO)
# =========================
def supertrend_last(df, period=10, multiplier=3):
    """
    Ritorna True se trend UP, False se DOWN
    Implementazione semplice, SCALARE e robusta
    """

    # Normalizza colonne (yfinance può restituire MultiIndex)
    df = df.copy()
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    required_cols = {"High", "Low", "Close"}
    if not required_cols.issubset(df.columns):
        raise ValueError("Colonne OHLC mancanti")

    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)

    hl2 = (high + low) / 2
    atr = (high - low).rolling(period).mean()

    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr

    trend_up = True

    for i in range(1, len(df)):
        if pd.isna(upperband.iloc[i - 1]) or pd.isna(lowerband.iloc[i - 1]):
            continue

        if close.iloc[i] > upperband.iloc[i - 1]:
            trend_up = True
        elif close.iloc[i] < lowerband.iloc[i - 1]:
            trend_up = False

    return trend_up

# =========================
# CALCOLO SUPERTREND
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
        data = yf.download(
            ticker,
            period="2y",
            interval="1wk",
            progress=False,
            auto_adjust=True
        )

        if data.empty or len(data) < 20:
            print(f"⚠️ Dati insufficienti per {ticker}")
            continue

        st_up = supertrend_last(data)

        rows.append({
            ticker_col: ticker,
            "ST_Weekly": "UP" if st_up else "DOWN"
        })

    except Exception as e:
        print(f"⚠️ Errore su {ticker}: {e}")

# =========================
# DATAFRAME SUPERTREND
# =========================
df_st = pd.DataFrame(rows)

if df_st.empty:
    print("⚠️ Nessun segnale SuperTrend calcolato")
    df_final = df_poc.copy()
else:
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
