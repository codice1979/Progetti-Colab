import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import os
import warnings

warnings.simplefilter('ignore', category=FutureWarning)

# =========================
# CONFIG
# =========================
TICKER = "P911.DE"

POC_CONFIGS = [
    {"poc_period": "20y", "soglia": 15},
    {"poc_period": "5y",  "soglia": 5},
    {"poc_period": "2y",  "soglia": 3},
]

filter_start_date = pd.to_datetime("2000-01-01")

# =========================
# FUNZIONI
# =========================
def get_hist(ticker, period):
    return yf.download(ticker, period=period, progress=False)

def calculate_drawdowns(prices):
    cummax = prices.cummax()
    drawdown = (cummax - prices) / cummax * 100
    return drawdown.max(), drawdown.mean(), drawdown.iloc[-1]

def get_poc_daily(ticker, period="5y", bins=200):
    df = yf.download(
        ticker,
        period=period,
        interval="1d",
        progress=False,
        auto_adjust=False
    )

    if df.empty:
        return None

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

# =========================
# ESECUZIONE
# =========================
results = []

df_last = get_hist(TICKER, "1d")
current_price = float(df_last["Close"].iloc[-1])

df_all = get_hist(TICKER, "max")
df_all = df_all[df_all.index >= filter_start_date]
close_prices = df_all["Close"]

ath = close_prices.max()
max_dd, avg_dd, current_dd = calculate_drawdowns(close_prices)

print(f"\n📊 TICKER: {TICKER}")
print(f"Prezzo attuale: {current_price:.2f}")
print("-" * 60)

for cfg in POC_CONFIGS:
    poc = get_poc_daily(TICKER, period=cfg["poc_period"])
    distanza = (current_price - poc) / poc * 100

    passa = abs(distanza) <= cfg["soglia"]

    print(
        f"POC {cfg['poc_period']:>3} | "
        f"POC={poc:.2f} | "
        f"Distanza={distanza:.2f}% | "
        f"Soglia={cfg['soglia']}% | "
        f"{'✅ PASSA' if passa else '❌ NON PASSA'}"
    )

    results.append({
        "Ticker": TICKER,
        "POC Period": cfg["poc_period"],
        "POC": poc,
        "Prezzo Attuale": current_price,
        "Distanza POC %": distanza,
        "Soglia %": cfg["soglia"],
        "Passa filtro": passa,
        "All Time High": ath,
        "Max Drawdown %": max_dd,
        "Avg Drawdown %": avg_dd,
        "Current Drawdown %": current_dd
    })

# =========================
# SALVATAGGIO
# =========================
df = pd.DataFrame(results)

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

week = datetime.now().isocalendar()[1]
file_path = os.path.join(
    OUTPUT_DIR,
    f"POC_DEBUG_{TICKER}_week_{week}.xlsx"
)

df.to_excel(file_path, index=False)

print(f"\n✅ File debug salvato: {file_path}")
