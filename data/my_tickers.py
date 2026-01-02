import requests
import pandas as pd

def get_tickers_from_wiki(url, column_name, suffix="", manual_list=None):
    """
    Scarica i ticker da Wikipedia con gestione suffissi Yahoo.
    Se lo scraping fallisce, usa la lista manuale di fallback.
    Gestisce eccezioni specifiche come ArcelorMittal (MT.AS).
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tables = pd.read_html(response.text)

        exceptions_no_suffix = ["MT.AS"]  # Lista eccezioni per cui non aggiungere suffisso

        for table in tables:
            if column_name in table.columns:
                tickers = []
                for t in table[column_name].dropna().unique():
                    ticker = str(t).strip()

                    # Eccezioni S&P 500
                    if ticker in ["BRK.B", "BF.B"]:
                        tickers.append(ticker.replace(".", "-"))
                        continue

                    # Normalizzazione generale
                    ticker = ticker.replace("-", ".")

                    # Non aggiunge suffisso se il ticker Ã¨ in exceptions_no_suffix
                    if ticker not in exceptions_no_suffix:
                        known_suffixes = [".DE", ".PA", ".MI"]
                        if suffix and not any(ticker.endswith(s) for s in known_suffixes):
                            ticker += suffix

                    tickers.append(ticker)

                if tickers:
                    return tickers

        # Se niente trovato, fallback manuale
        if manual_list:
            return manual_list
        return []

    except Exception as e:
        print(f"â Errore caricamento da {url}: {e}")
        if manual_list:
            print("â¡ Uso lista manuale di fallback")
            return manual_list
        return []

def get_all_tickers(flat=True):
    """
    Raccoglie ticker da piÃ¹ indici + lista manuale.
    Se flat=True ritorna una lista unica (senza duplicati).
    Se flat=False ritorna un dizionario con i ticker per indice.
    """

    # Liste manuali complete
    ftse_mib_manual = [
        "A2A.MI","AMP.MI","AZM.MI","BMED.MI","BMPS.MI","BAMI.MI","BPSO.MI","BPE.MI",
        "BC.MI","BZU.MI","CPR.MI","DIA.MI","ENEL.MI","ENI.MI","RACE.MI","FBK.MI",
        "G.MI","HER.MI","IP.MI","ISP.MI","INW.MI","IG.MI","IVG.MI","LDO.MI",
        "MB.MI","MONC.MI","NEXI.MI","PIRC.MI","PST.MI","PRY.MI","REC.MI","SPM.MI",
        "SRG.MI","STLAM.MI","STMMI.MI","TIT.MI","TEN.MI","TRN.MI","UCG.MI","UNI.MI"
    ]

    cac40_manual = [
        "AC.PA","AI.PA","AIR.PA","MT.AS","CS.PA","BNP.PA","EN.PA","CAP.PA","CA.PA",
        "ACA.PA","BN.PA","DSY.PA","EDEN.PA","ENGI.PA","EL.PA","ERF.PA","RMS.PA",
        "KER.PA","OR.PA","LR.PA","MC.PA","ML.PA","ORA.PA","RI.PA","PUB.PA","RNO.PA",
        "SAF.PA","SGO.PA","SAN.PA","SU.PA","GLE.PA","STLAP.PA","STMPA.PA","TEP.PA",
        "HO.PA","TTE.PA","URW.PA","VIE.PA","DG.PA","VIV.PA"
    ]

    all_tickers = {}

    # S&P 500
    sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    all_tickers["sp500"] = get_tickers_from_wiki(sp500_url, "Symbol")

    # Nasdaq-100
    nasdaq_url = "https://en.wikipedia.org/wiki/NASDAQ-100"
    all_tickers["nasdaq100"] = get_tickers_from_wiki(nasdaq_url, "Ticker")

    # DAX (Germania, .DE)
    dax_url = "https://en.wikipedia.org/wiki/DAX"
    all_tickers["dax"] = get_tickers_from_wiki(dax_url, "Ticker", suffix=".DE")

    # FTSE MIB (Italia, .MI) con fallback manuale
    ftse_url = "https://en.wikipedia.org/wiki/FTSE_MIB"
    all_tickers["ftse_mib"] = get_tickers_from_wiki(ftse_url, "Ticker", suffix=".MI", manual_list=ftse_mib_manual)

    # CAC 40 (Francia, .PA) con fallback manuale
    cac_url = "https://en.wikipedia.org/wiki/CAC_40"
    all_tickers["cac40"] = get_tickers_from_wiki(cac_url, "Ticker", suffix=".PA", manual_list=cac40_manual)

    # Extra strumenti
    all_tickers["extra"] = [
        "^GSPC","^NDX","^GDAXI","GC=F","SI=F","CL=F","^VIX",
        "EURUSD=X","BTC-USD","ETH-USD"
    ]

    if flat:
        flat_list = [t for sublist in all_tickers.values() for t in sublist]
        flat_list = list(set(flat_list))
        print("ð Totale ticker raccolti:", len(flat_list))
        return flat_list
    else:
        for k, v in all_tickers.items():
            print(f"â {k}: {len(v)}")
        return all_tickers
