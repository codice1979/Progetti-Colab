import os
from datetime import datetime
import subprocess

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# =========================
# CONFIGURAZIONE BASE
# =========================
BASE_DIR = "./data"
POC_SCRIPT = os.path.join(BASE_DIR, "poc_all_tickers.py")
ST_SCRIPT = os.path.join(BASE_DIR, "merge_poc_supertrend.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ID CARTELLA GOOGLE DRIVE (quella che hai condiviso)
DRIVE_FOLDER_ID = "1BLzEbOTRiBtFRZGmrNhRAYXTyP8Nd3Hj"

# =========================
# CONFIGURAZIONI POC
# =========================
configs = [
    {"poc_period": 20, "soglia_poc": 15},
    {"poc_period": 5, "soglia_poc": 5}
]

week_number = datetime.now().isocalendar()[1]

# =========================
# AUTENTICAZIONE GOOGLE DRIVE
# =========================
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

credentials = service_account.Credentials.from_service_account_file(
    "service_account_credentials.json",
    scopes=SCOPES
)

drive_service = build("drive", "v3", credentials=credentials)

def upload_to_drive(filepath):
    file_metadata = {
        "name": os.path.basename(filepath),
        "parents": [DRIVE_FOLDER_ID]
    }

    media = MediaFileUpload(
        filepath,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    print(f"✅ Caricato su Drive: {os.path.basename(filepath)}")

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

    # 1️⃣ POC
    ret_poc = subprocess.run(
        ["python", POC_SCRIPT, "--poc_period", poc_period_cli, "--soglia_poc", soglia_poc]
    )

    if ret_poc.returncode != 0:
        print("❌ Errore POC")
        continue

    upload_to_drive(poc_file)

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

    if os.path.exists(st_file):
        upload_to_drive(st_file)

print("\n✅ WORKFLOW COMPLETATO CON SUCCESSO")
