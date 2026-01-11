import os
import sys
from datetime import datetime
import subprocess

# =========================
# CONFIGURAZIONE BASE
# =========================
BASE_DIR = "./data"
POC_SCRIPT = os.path.join(BASE_DIR, "poc_all_tickers.py")
ST_SCRIPT = os.path.join(BASE_DIR, "merge_poc_supertrend.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# aggiunge la cartella data ai moduli
sys.path.append(os.path.join(os.getcwd(), "data"))

from my_tickers import get_all_tickers

# =========================
# CONFIGURAZIONI POC
# =========================
configs = [
    {"poc_period": 20, "soglia_poc": 15},
    {"poc_period": 5,  "soglia_poc": 5},
    {"poc_period": 2,  "soglia_poc": 3}
]

week_number = datetime.now().isocalendar()[1]

# =========================
# ESECUZIONE MASTER
# =========================
for cfg in configs:
    poc_period_cli = str(cfg["poc_period"])
    poc_period_file = f"{cfg['poc_period']}y"
    soglia_poc = str(cfg["soglia_poc"])

    print(f"\n=== POC {poc_period_file} | soglia {soglia_poc} ===")

    poc_file = os.path.join(
        OUTPUT_DIR,
        f"POC_p{poc_period_file}_s{soglia_poc}_week_{week_number}.xlsx"
    )

    # 1️⃣ POC (serve comunque per il merge)
    ret_poc = subprocess.run(
        ["python", POC_SCRIPT, "--poc_period", poc_period_cli, "--soglia_poc", soglia_poc]
    )

    if ret_poc.returncode != 0:
        print("❌ Errore POC")
        continue

    print(f"✅ POC calcolato")

    # 2️⃣ MERGE + SUPERTREND
    ret_st = subprocess.run(
        ["python", ST_SCRIPT, "--poc_period", poc_period_file, "--soglia_poc", soglia_poc]
    )

    if ret_st.returncode != 0:
        print("❌ Errore SuperTrend")
        continue

    st_file = os.path.join(
        OUTPUT_DIR,
        f"POC_ST_p{poc_period_file}_s{soglia_poc}_week_{week_number}.xlsx"
    )

    print(f"✅ File salvato: {st_file}")

    # 🧹 ELIMINA FILE POC INTERMEDIO
    if os.path.exists(poc_file):
        os.remove(poc_file)
        print(f"🗑️ File POC rimosso: {os.path.basename(poc_file)}")
