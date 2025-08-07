import requests
import pandas as pd
import logging
import time
import os
import json
from datetime import datetime

# === CONFIGURATION ===
API_KEY = "c4vKgNXnXUw9YQjnUuD5gRU2MsDLTRwP"  # ← ta clé FMP
CSV_PATH = "../data/micro_caps_extended.csv"
JSON_DIR = "../data/evolution"
LOG_PATH = "../logs/microcap_fetch.log"

CAP_MIN = 50_000_000
CAP_MAX = 300_000_000
STEP = 25_000_000  # tranche de market cap
PAUSE = 3  # secondes entre appels pour rester safe

# === SETUP LOGGING ===
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
logging.getLogger().addHandler(console)

# === APPEL API FMP POUR UNE TRANCHE ===
def fetch_screener_batch(mc_min, mc_max):
    url = "https://financialmodelingprep.com/api/v3/stock-screener"
    params = {
        "marketCapMoreThan": mc_min,
        "marketCapLowerThan": mc_max,
        "exchange": "nasdaq,nyse,amex",
        "volumeMoreThan": 0,
        "limit": 1000,
        "apikey": API_KEY
    }
    try:
        logging.info(f"Fetching batch: {mc_min/1e6:.0f}M – {mc_max/1e6:.0f}M")
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        time.sleep(PAUSE)
        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Erreur batch {mc_min}-{mc_max}: {e}")
        return pd.DataFrame()

# === ENREGISTREMENT JSON SNAPSHOT JOURNALIER ===
def save_daily_snapshot_json(df):
    os.makedirs(JSON_DIR, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    snapshot_path = os.path.join(JSON_DIR, f"caps_evolution_{today_str}.json")

    # Convertir en dict
    snapshot_data = df.to_dict(orient="records")

    # Charger JSON existant si présent
    if os.path.exists(snapshot_path):
        with open(snapshot_path, "r", encoding="utf-8") as f:
            all_snapshots = json.load(f)
    else:
        all_snapshots = {}

    # Ajouter le snapshot sous clé horodatée
    all_snapshots[now_str] = snapshot_data

    # Sauvegarder
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(all_snapshots, f, ensure_ascii=False, indent=2)

    logging.info(f"📌 Snapshot JSON sauvegardé dans {snapshot_path}")

# === FONCTION PRINCIPALE ===
def fetch_all_microcaps():
    logging.info("🟢 Démarrage de la récupération micro-caps")
    all_batches = []

    for cap in range(CAP_MIN, CAP_MAX, STEP):
        batch = fetch_screener_batch(cap, cap + STEP)
        if not batch.empty:
            all_batches.append(batch)

    if not all_batches:
        logging.error("❌ Aucun batch récupéré.")
        return

    combined = pd.concat(all_batches, ignore_index=True).drop_duplicates(subset="symbol")
    logging.info(f"📦 Total microcaps récupérées : {len(combined)}")

    # Nettoyage et renommage
    df = combined[["symbol", "companyName", "marketCap", "price", "sector", "exchangeShortName", "volume"]].copy()
    df = df.rename(columns={
        "symbol": "Ticker",
        "companyName": "Name",
        "marketCap": "Market Cap",
        "price": "Price",
        "sector": "Sector",
        "exchangeShortName": "Market",
        "volume": "Volume"
    })

    # Nettoyage : supprimer les espaces dans les noms de secteurs et marchés
    df["Sector"] = df["Sector"].str.replace(" ", "")
    df["Market"] = df["Market"].str.replace(" ", "")
    logging.info("🧼 Nettoyage des espaces dans les secteurs et marchés")

    # Sauvegarde CSV
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    df.to_csv(CSV_PATH, index=False)
    logging.info(f"✅ Fichier exporté : {CSV_PATH}")

    # Sauvegarde JSON (historique)
    save_daily_snapshot_json(df)

if __name__ == "__main__":
    fetch_all_microcaps()
