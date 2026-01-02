# ============================================
# CODICE 3 -  Merge POC + SuperTrend multiperiodo
# ============================================

import subprocess
import sys
import os # Moved os import to the top
import contextlib # Moved contextlib import to the top
import argparse



# Funzione per installare i pacchetti
def install_packages():
    packages = ['yfinance', 'pandas', 'numpy', 'TA-Lib']
    for package in packages:
        try:
            # Suppress output for pip install
            with open(os.devnull, 'w') as f:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package], stdout=f, stderr=f)
            print(f"Installato {package} con successo")
        except:
            print(f"Errore nell'installazione di {package}")

# Installa i pacchetti necessari
install_packages()

# Importa le librerie
try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    import talib as ta
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
  

except ImportError as e:
    print(f"Errore nell'importazione delle librerie: {e}")
    # Non uscire qui, permetti all'utente di vedere l'errore e risolverlo
    # sys.exit(1)

    import argparse
import os
from datetime import datetime

parser = argparse.ArgumentParser(description="Supertrend su file POC")
parser.add_argument(
    "--poc_period",
    type=str,
    required=True,
    help="Periodo POC (es. '5y', '10y', '20y')"
)
parser.add_argument(
    "--soglia_poc",
    type=int,
    required=True,
    help="Soglia percentuale usata nel file POC"
)

args = parser.parse_args()

poc_period = args.poc_period
soglia_poc = args.soglia_poc


BASE = "/content/drive/MyDrive/automatico"
OUTPUT_DIR = f"{BASE}/output"

week_number = datetime.now().isocalendar()[1]

poc_file_path = os.path.join(
    OUTPUT_DIR,
    f"POC_p{poc_period}_s{soglia_poc}_week_{week_number}.xlsx"
)

print("Cerco file POC in:")
print(poc_file_path)

if not os.path.exists(poc_file_path):
    raise FileNotFoundError(f"❌ File POC non trovato: {poc_file_path}")


try:
  # Suppress output when loading the Excel file
  with open(os.devnull, 'w') as f:
    with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
      df_poc = pd.read_excel(poc_file_path)

  print("File POC caricato con successo.")

except FileNotFoundError:
    print(f"Errore: File POC non trovato in {poc_file_path}.")
    print("Assicurati che la cella precedente sia stata eseguita correttamente e che il file esista.")
    # Non uscire qui, permetti al codice di continuare (anche con un dataframe vuoto)
    df_poc = pd.DataFrame() # Crea un dataframe vuoto per evitare errori successivi
except Exception as e:
    print(f"Errore caricamento file POC: {e}")
    # Non uscire qui
    df_poc = pd.DataFrame() # Crea un dataframe vuoto per evitare errori successivi

# Procedi solo se il dataframe POC non è vuoto
if not df_poc.empty:

  # === 2. Funzioni di supporto per SuperTrend TradingView ===
  def calculate_supertrend(high, low, close, atr_period, multiplier):
      """Calcola il Supertrend"""

      # Ensure inputs are numpy arrays
      high = np.asarray(high)
      low = np.asarray(low)
      close = np.asarray(close)

      if len(high) < atr_period or len(low) < atr_period or len(close) < atr_period or atr_period <= 0:
          # print("Dati insufficienti per calcolare Supertrend.") # Opzionale: stampa un messaggio
          return np.full_like(close, np.nan), np.full_like(close, np.nan)

      # Calcolo ATR
      atr = ta.ATR(high, low, close, timeperiod=atr_period)

      # Calcolo delle bande
      upperband = (high + low) / 2 + (multiplier * atr)
      lowerband = (high + low) / 2 - (multiplier * atr)

      # Inizializza Supertrend
      supertrend = np.full_like(close, np.nan)
      direction = np.full_like(close, np.nan)

      # Find the first valid index after ATR calculation
      first_valid_atr_idx = np.where(~np.isnan(atr))[0][0] if np.any(~np.isnan(atr)) else len(close)

      if first_valid_atr_idx >= len(close):
          # print("ATR non calcolabile per periodo specificato.") # Opzionale: stampa un messaggio
          return np.full_like(close, np.nan), np.full_like(close, np.nan)

      # Initialize first valid Supertrend value
      supertrend[first_valid_atr_idx] = upperband[first_valid_atr_idx]
      direction[first_valid_atr_idx] = 1

      # Calcola Supertrend
      for i in range(first_valid_atr_idx + 1, len(close)):
          # Use previous valid supertrend value if the current one is nan (can happen with short data)
          prev_supertrend = supertrend[i-1] if not np.isnan(supertrend[i-1]) else (upperband[i-1] + lowerband[i-1]) / 2 # Fallback if prev is nan

          if close[i] > prev_supertrend:
              direction[i] = 1
          else:
              direction[i] = -1

          if direction[i] == 1:
              if lowerband[i] > prev_supertrend:
                  supertrend[i] = lowerband[i]
              else:
                  supertrend[i] = prev_supertrend
          else:
              if upperband[i] < prev_supertrend:
                  supertrend[i] = upperband[i]
              else:
                  supertrend[i] = prev_supertrend

      # Backfill NaNs at the beginning with the first valid Supertrend value
      first_valid_st_idx = np.where(~np.isnan(supertrend))[0][0] if np.any(~np.isnan(supertrend)) else len(close)
      if first_valid_st_idx < len(close):
          supertrend[:first_valid_st_idx] = supertrend[first_valid_st_idx]

      return supertrend, direction

  def calculate_start_date(interval):
      """Calcola la data di inizio per il download dei dati in base all'intervallo."""
      today = datetime.now()
      if interval == "1d":
          # 6 mesi per il daily
          return today - relativedelta(months=6)
      elif interval == "1wk":
          # 1 anno per il weekly
          return today - relativedelta(years=1)
      elif interval == "1mo":
          # 2 anni per il monthly
          return today - relativedelta(years=2)
      elif interval == "4h":
          # 60 giorni per il 4h
          return today - timedelta(days=60)
      else:
          return None # O gestisci altri intervalli se necessario

  def fix_df(df):
      """Rimuove MultiIndex e converte colonne in float"""
      if isinstance(df.columns, pd.MultiIndex):
          df.columns = [col[0] for col in df.columns]
      for col in ['Open','High','Low','Close','Adj Close','Volume']:
          if col in df.columns:
              # Use errors='coerce' to turn problematic values into NaN
              df[col] = pd.to_numeric(df[col], errors='coerce')
              # Drop rows with NaN in critical columns if necessary, or handle NaNs later
              # df.dropna(subset=[col], inplace=True) # Uncomment if dropping rows with NaN is desired

      # Ensure index is datetime
      if not isinstance(df.index, pd.DatetimeIndex):
          df.index = pd.to_datetime(df.index, errors='coerce')
          df.dropna(inplace=True) # Drop rows where index couldn't be converted

      return df

  # === 3. Funzione che calcola ST per 4H/Daily/Weekly/Monthly ===
  def get_supertrend_signals(ticker, atr_period=10, multiplier=3.0):
      try:
          # Suppress output when downloading data
          with open(os.devnull, 'w') as f:
            with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
              start_date_daily = calculate_start_date("1d")
              start_date_weekly = calculate_start_date("1wk")
              start_date_monthly = calculate_start_date("1mo")
              start_date_4h = calculate_start_date("4h")

              # Added check for start_date being None
              df_daily = fix_df(yf.download(ticker, start=start_date_daily, interval="1d", auto_adjust=True) if start_date_daily else pd.DataFrame())
              df_weekly = fix_df(yf.download(ticker, start=start_date_weekly, interval="1wk", auto_adjust=True) if start_date_weekly else pd.DataFrame())
              df_monthly = fix_df(yf.download(ticker, start=start_date_monthly, interval="1mo", auto_adjust=True) if start_date_monthly else pd.DataFrame())
              df_4h = fix_df(yf.download(ticker, start=start_date_4h, interval="4h", auto_adjust=True) if start_date_4h else pd.DataFrame())

          # Added checks for required columns after fixing df
          close_price = df_poc[df_poc['Ticker'] == ticker]['Prezzo Attuale'].iloc[0] if ticker in df_poc['Ticker'].values else np.nan

          st_4h_val = np.nan
          if not df_4h.empty and 'Close' in df_4h.columns and 'High' in df_4h.columns and 'Low' in df_4h.columns:
              st_4h, dir_4h = calculate_supertrend(df_4h['High'], df_4h['Low'], df_4h['Close'], atr_period, multiplier)
              st_4h_last = st_4h[-1] if not np.isnan(st_4h[-1]) else np.nan
              # Modified calculation to use ST as denominator if ST is not zero
              if not np.isnan(st_4h_last) and not np.isnan(close_price) and st_4h_last != 0:
                  st_4h_val = ((close_price - st_4h_last) / st_4h_last) * 100
              elif not np.isnan(close_price) and close_price != 0: # Handle case where ST is zero or NaN, but price is valid
                   st_4h_val = ((close_price - st_4h_last) / close_price) * 100 # Fallback to price as denominator
              else:
                   st_4h_val = np.nan

          st_daily_val = np.nan
          if not df_daily.empty and 'Close' in df_daily.columns and 'High' in df_daily.columns and 'Low' in df_daily.columns:
              st_daily, dir_daily = calculate_supertrend(df_daily['High'], df_daily['Low'], df_daily['Close'], atr_period, multiplier)
              st_daily_last = st_daily[-1] if not np.isnan(st_daily[-1]) else np.nan
              # Modified calculation to use ST as denominator if ST is not zero
              if not np.isnan(st_daily_last) and not np.isnan(close_price) and st_daily_last != 0:
                  st_daily_val = ((close_price - st_daily_last) / st_daily_last) * 100
              elif not np.isnan(close_price) and close_price != 0: # Handle case where ST is zero or NaN, but price is valid
                   st_daily_val = ((close_price - st_daily_last) / close_price) * 100 # Fallback to price as denominator
              else:
                   st_daily_val = np.nan

          st_weekly_val = np.nan
          if not df_weekly.empty and 'Close' in df_weekly.columns and 'High' in df_weekly.columns and 'Low' in df_weekly.columns:
              st_weekly, dir_weekly = calculate_supertrend(df_weekly['High'], df_weekly['Low'], df_weekly['Close'], atr_period, multiplier)
              st_weekly_last = st_weekly[-1] if not np.isnan(st_weekly[-1]) else np.nan
              # Modified calculation to use ST as denominator if ST is not zero
              if not np.isnan(st_weekly_last) and not np.isnan(close_price) and st_weekly_last != 0:
                  st_weekly_val = ((close_price - st_weekly_last) / st_weekly_last) * 100
              elif not np.isnan(close_price) and close_price != 0: # Handle case where ST is zero or NaN, but price is valid
                   st_weekly_val = ((close_price - st_weekly_last) / close_price) * 100 # Fallback to price as denominator
              else:
                   st_weekly_val = np.nan

          st_monthly_val = np.nan
          if not df_monthly.empty and 'Close' in df_monthly.columns and 'High' in df_monthly.columns and 'Low' in df_monthly.columns:
              st_monthly, dir_monthly = calculate_supertrend(df_monthly['High'], df_monthly['Low'], df_monthly['Close'], atr_period, multiplier)
              st_monthly_last = st_monthly[-1] if not np.isnan(st_monthly[-1]) else np.nan
              # Modified calculation to use ST as denominator if ST is not zero
              if not np.isnan(st_monthly_last) and not np.isnan(close_price) and st_monthly_last != 0:
                  st_monthly_val = ((close_price - st_monthly_last) / st_monthly_last) * 100
              elif not np.isnan(close_price) and close_price != 0: # Handle case where ST is zero or NaN, but price is valid
                   st_monthly_val = ((close_price - st_monthly_last) / close_price) * 100 # Fallback to price as denominator
              else:
                   st_monthly_val = np.nan

          return st_4h_val, st_daily_val, st_weekly_val, st_monthly_val

      except Exception as e:
          print(f"Errore durante il calcolo del SuperTrend per {ticker}: {e}")
          return np.nan, np.nan, np.nan, np.nan

  # === 4. Applica ai ticker del file POC ===
  df_poc[['ST_4H','ST_Daily','ST_Weekly','ST_Monthly']] = df_poc['Ticker'].apply(
      lambda x: pd.Series(get_supertrend_signals(x))
  )

  print("\nTabella finale con segnali SuperTrend:")

  # Identifica le colonne numeriche da formattare (escludi 'POC' che potrebbe avere molti decimali se calcolato)
  # e le colonne di tipo oggetto (stringhe come 'Ticker', 'Indice')
  numeric_cols_to_format = df_poc.select_dtypes(include=np.number).columns.tolist()
  # Rimuovi 'POC' dalla lista se presente e se non vuoi formattarlo con un solo decimale
  if 'POC' in numeric_cols_to_format:
      # Puoi scegliere se formattare anche POC o no. Qui lo rimuoviamo per lasciarlo come è.
      # Se vuoi formattarlo, commenta la riga successiva:
      # numeric_cols_to_format.remove('POC')
      pass # Lascia POC nella lista per formattarlo con 1 decimale

  # Applica la formattazione a tutte le colonne numeriche identificate
  format_mapping = {col: '{:.1f}'.format for col in numeric_cols_to_format}

  df_poc_display = df_poc.copy()
  for col, formatter in format_mapping.items():
      if col in df_poc_display.columns:
          # Handle potential NaN values before formatting
          df_poc_display[col] = df_poc_display[col].apply(lambda x: formatter(x).replace('.', ',') if pd.notna(x) else 'NaN')

  print(df_poc_display.to_string())


# === 5. Esporta in Excel ===

BASE_DIR = "/content/drive/MyDrive/automatico"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

week_number = datetime.now().isocalendar()[1]

output_file_path = os.path.join(
    OUTPUT_DIR,
    f"POC_ST_p{poc_period}_s{soglia_poc}_week_{week_number}.xlsx"
)

df_poc_export = df_poc.copy()

# Formattazione colonne numeriche (1 decimale, virgola)
for col, formatter in format_mapping.items():
    if col in df_poc_export.columns:
        df_poc_export[col] = df_poc_export[col].apply(
            lambda x: formatter(x).replace('.', ',') if pd.notna(x) else ''
        )

df_poc_export.to_excel(output_file_path, index=False)

print(f"\n✅ File POC + SuperTrend esportato in:\n{output_file_path}")


