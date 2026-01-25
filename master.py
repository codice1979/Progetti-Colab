import os
import sys
import subprocess
from datetime import datetime

# =========================
# CONFIGURAZIONE BASE
# =========================

# Path assoluto della cartella root del progetto
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Cartella data
BASE_DIR = os.path.join(ROOT_DIR, "data")

# Script POC e merge Supertrend
POC_SCRIPT = os.path.join(BASE_DIR, "poc_all_tickers.py")
ST_SCRIPT = os.path.join(BASE_DIR, "merge_poc_supertrend.py")

# Output
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Aggiunge la cartella data ai moduli Python
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from my_tickers import get_all_tickers  # noqa: E402

print("✅ Avvio master.py")
print(f"📂 ROOT_DIR: {ROOT_DIR}")
print(f"📂 BASE_DIR: {BASE_DIR}")
print(f"📂 OUTPUT_DIR: {OUTPUT_DIR}")

# =========================
# CONFIGURAZIONI POC
# =========================
CONFIGS = [
    {"poc_period": 20, "soglia_poc": 15},
    {"poc_period": 5,  "soglia_poc": 5},
    {"poc_period": 2,  "soglia_poc": 3},
]

# Numero settimana ISO
week_number = datetime.now().isocalendar()[1]

print(f"📅 Settimana ISO: {week_number}")

# =========================
# ESECUZIONE MASTER
# =========================

for cfg in CONFIGS:
    poc_period = cfg["poc_period"]
    soglia_poc = cfg["soglia_poc"]

    poc_period_cli = str(poc_period)     # per CLI script POC
    poc_period_file = f"{poc_period}y"   # per naming file

    print("\n" + "=" * 60)
    print(f"🚀 POC = {poc_period_cli} | soglia = {soglia_poc}")
    print("=" * 60)

    # Nome file POC intermedio
    poc_file = os.path.join(
        OUTPUT_DIR,
        f"POC_p{poc_period_file}_s{soglia_poc}_week_{week_number}.xlsx"
    )

    # Nome file finale merge + SuperTrend
    st_file = os.path.join(
        OUTPUT_DIR,
        f"POC_ST_p{poc_period_file}_s{soglia_poc}_week_{week_number}.xlsx"
    )

    # =========================
    # 1️⃣ ESECUZIONE POC
    # =========================
    print("▶️ Avvio script POC...")

    ret_poc = subprocess.run(
        ["python", POC_SCRIPT, "--poc_period", poc_period_cli, "--soglia_poc", str(soglia_poc)],
        cwd=ROOT_DIR
    )

    if ret_poc.returncode != 0:
        print(f"❌ Errore nello script POC (period={poc_period_cli}, soglia={soglia_poc})")
        continue

    if not os.path.exists(poc_file):
        print(f"⚠️ File POC non trovato: {poc_file}")
        continue

    print(f"✅ POC calcolato: {os.path.basename(poc_file)}")

    # =========================
    # 2️⃣ MERGE + SUPERTREND
    # =========================
    print("▶️ Avvio merge POC + SuperTrend...")

    ret_st = subprocess.run(
        ["python", ST_SCRIPT, "--poc_period", poc_period_file, "--soglia_poc", str(soglia_poc)],
        cwd=ROOT_DIR
    )

    if ret_st.returncode != 0:
        print(f"❌ Errore nello script SuperTrend (period={poc_period_file}, soglia={soglia_poc})")
        continue

    if not os.path.exists(st_file):
        print(f"⚠️ File finale non trovato: {st_file}")
        continue

    print(f"✅ File finale creato: {os.path.basename(st_file)}")

    # =========================
    # 🧹 CANCELLA FILE POC INTERMEDIO
    # =========================
    try:
        if os.path.exists(poc_file):
            os.remove(poc_file)
            print(f"🗑️ File POC rimosso: {os.path.basename(poc_file)}")
    except Exception as e:
        print(f"⚠️ Impossibile cancellare {poc_file}: {e}")

print("\n🎯 Master completato con successo.")
