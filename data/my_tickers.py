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


def get_all_tickers(flat=True):
    """
    Raccoglie ticker da più indici + lista manuale.
    """

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

    all_tickers["sp500"] = get_tickers_from_wiki(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "Symbol"
    )

    all_tickers["nasdaq100"] = get_tickers_from_wiki(
        "https://en.wikipedia.org/wiki/NASDAQ-100", "Ticker"
    )

    all_tickers["dax"] = get_tickers_from_wiki(
        "https://en.wikipedia.org/wiki/DAX", "Ticker", suffix=".DE"
    )

    all_tickers["ftse_mib"] = get_tickers_from_wiki(
        "https://en.wikipedia.org/wiki/FTSE_MIB", "Ticker", suffix=".MI", manual_list=ftse_mib_manual
    )

    all_tickers["cac40"] = get_tickers_from_wiki(
        "https://en.wikipedia.org/wiki/CAC_40", "Ticker", suffix=".PA", manual_list=cac40_manual
    )

    all_tickers["extra"] = [
        "^GSPC","^NDX","^GDAXI","GC=F","SI=F","CL=F","^VIX",
        "EURUSD=X","BTC-USD","ETH-USD",
        "CRCL","QUBT","SMR","NOVO-B.CO","P911.DE","PUM.DE",
        "ENPH","UPS","BABA","NIO","OKLO"
    ]

    if flat:
        flat_list = sorted(set(t for sub in all_tickers.values() for t in sub))
        print("🔎 Totale ticker raccolti:", len(flat_list))
        return flat_list
    else:
        for k, v in all_tickers.items():
            print(f"✅ {k}: {len(v)}")
        return all_tickers
