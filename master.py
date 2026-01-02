import os
from datetime import datetime
import subprocess
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# =========================
# CONFIGURAZIONE BASE
# =========================

BASE_DIR = "./data"
POC_SCRIPT = os.path.join(BASE_DIR, "poc_all_tickers.py")
ST_SCRIPT = os.path.join(BASE_DIR, "merge_poc_supertrend.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# CONFIGURAZIONI POC
configs = [
    {"poc_period": 20, "soglia_poc": 15},
    {"poc_period": 5, "soglia_poc": 5}
]

week_number = datetime.now().isocalendar()[1]

# =========================
# AUTENTICAZIONE GOOGLE DRIVE (SERVICE ACCOUNT)
# =========================

gauth = GoogleAuth()
gauth.settings['client_config_file'] = 'service_account_credentials.json'
gauth.ServiceAuth()

drive = GoogleDrive(gauth)

# ID CARTELLA DRIVE (QUELLA CHE HAI CONDIVISO)
DRIVE_FOLDER_ID = "1BLzEbOTRiBtFRZGmrNhRAYXTyP8Nd3Hj"

# =========================
# ESECUZIONE
# =========================

for cfg in configs:
    poc_period_cli = str(cfg["poc_period"])
    poc_period_file = f"{cfg['poc_period']}y"
    soglia_poc = str(cfg["soglia_poc"])

    print(f"\n=== POC {poc_period_file} | soglia {soglia_poc} ===")

    poc_file = os.path.join(
        OUTPUT_DIR, f"POC_p{poc_period_file}_s{soglia_poc}_week_{week_number}.xlsx"
    )

    # 1️⃣ POC
    ret_poc = subprocess.run(
        ["python3", POC_SCRIPT, "--poc_period", poc_period_cli, "--soglia_poc", soglia_poc],
        check=False
    )

    if ret_poc.returncode != 0:
        print("❌ Errore POC")
        continue

    # 2️⃣ MERGE + SUPERTREND
    ret_st = subprocess.run(
        ["python3", ST_SCRIPT, "--poc_period", poc_period_file, "--soglia_poc", soglia_poc],
        check=False
    )

    if ret_st.returncode != 0:
        print("❌ Errore SuperTrend")
        continue

    # 3️⃣ UPLOAD SU DRIVE
    for f in os.listdir(OUTPUT_DIR):
        full_path = os.path.join(OUTPUT_DIR, f)
        if os.path.isfile(full_path):
            file_drive = drive.CreateFile({
                'title': f,
                'parents': [{'id': DRIVE_FOLDER_ID}]
            })
            file_drive.SetContentFile(full_path)
            file_drive.Upload()
            print(f"✅ Caricato: {f}")

print("\n✅ PIPELINE COMPLETATA")
