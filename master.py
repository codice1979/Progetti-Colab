import os
from datetime import datetime
import subprocess
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# --- Configurazione cartelle locali ---
BASE_DIR = "./data"
POC_SCRIPT = os.path.join(BASE_DIR, "poc_all_tickers.py")
ST_SCRIPT = os.path.join(BASE_DIR, "merge_poc_supertrend.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Configurazioni POC da eseguire ---
configs = [
    {"poc_period": 20, "soglia_poc": 15},
    {"poc_period": 5, "soglia_poc": 5}
]

# --- Numero settimana corrente ---
week_number = datetime.now().isocalendar()[1]

# --- Autenticazione Google Drive tramite Service Account ---
gauth = GoogleAuth()
gauth.LoadServiceConfigFile("service_account_credentials.json")  # JSON del SA salvato nella repo
drive = GoogleDrive(gauth)

# --- Inizio ciclo di esecuzione ---
for cfg in configs:
    poc_period_cli = str(cfg["poc_period"])
    poc_period_file = f"{cfg['poc_period']}y"
    soglia_poc = str(cfg["soglia_poc"])

    print(f"\n=== Esecuzione POC per poc_period={poc_period_file}, soglia_poc={soglia_poc} ===")

    poc_file = os.path.join(
        OUTPUT_DIR, f"POC_p{poc_period_file}_s{soglia_poc}_week_{week_number}.xlsx"
    )

    # === 1. POC ===
    print(f"Generazione file POC: {poc_file}")
    ret_poc = subprocess.run(
        ["python3", POC_SCRIPT, "--poc_period", poc_period_cli, "--soglia_poc", soglia_poc]
    )
    if ret_poc.returncode != 0:
        print(f"❌ Errore durante POC per {poc_period_file}, {soglia_poc}")
        continue
    print(f"✅ POC completato: {poc_file}")

    # === 2. MERGE + SUPERTREND ===
    print(f"Generazione SuperTrend basato su: {poc_file}")
    ret_st = subprocess.run(
        ["python3", ST_SCRIPT, "--poc_period", poc_period_file, "--soglia_poc", soglia_poc]
    )
    if ret_st.returncode != 0:
        print(f"❌ Errore durante SuperTrend per {poc_period_file}, {soglia_poc}")
        continue
    print(f"✅ SuperTrend completato per poc_period={poc_period_file}, soglia_poc={soglia_poc}")

    # === 3. Carica file POC + SuperTrend su Google Drive ===
    for f in [poc_file, os.path.join(OUTPUT_DIR, f"POC_ST_p{poc_period_file}_s{soglia_poc}_week_{week_number}.xlsx")]:
        if os.path.exists(f):
            file_drive = drive.CreateFile({'title': os.path.basename(f), 'parents':[{'id':'YOUR_FOLDER_ID'}]})
            file_drive.SetContentFile(f)
            file_drive.Upload()
            print(f"✅ Caricato su Drive: {f}")

print("\n✅ Tutte le esecuzioni completate.")
