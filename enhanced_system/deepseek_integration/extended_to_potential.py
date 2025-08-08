import os
import re
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Any
import math

import pandas as pd
import numpy as np

# Permettre l'import du paquet racine lors d'une exécution directe de ce script
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from enhanced_system.common.utils import (
    validate_csv_columns,
    normalize_ticker,
    normalize_exchange,
    safe_ensure_dir,
    write_json_atomic,
    acquire_lock,
    release_lock,
)


# =========================
# Configuration défauts
# =========================

DATA_DIR = "enhanced_system/data"
EVOL_DIR = os.path.join(DATA_DIR, "evolution")

INPUT_CSV = os.path.join(DATA_DIR, "micro_caps_extended.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "extended_to_potential.csv")

PRIORITY_EXCHANGES = {"NASDAQ"}
PRIORITY_SECTORS = {"TECH", "TECHNOLOGY", "HEALTHCARE", "HEALTH CARE"}

# Seuils (simples, paramétrables plus tard si besoin)
MC_MIN = 50_000_000
MC_MAX = 200_000_000  # peut être abaissé à 150M si souhaité
PRICE_MIN = 5.0
PREFERRED_PRICE_MAX = 10.0
VOLUME_SOFT_MIN = 10_000


def _choose_schedule_slot(paris_dt: datetime) -> str:
    slots = ["09:00", "14:30", "18:00", "22:00", "01:30"]
    # Retourne le slot le plus proche en dessous (ou le premier si après minuit)
    hm = int(paris_dt.strftime("%H%M"))
    order = [900, 1430, 1800, 2200, 130]  # tri logique sur la journée
    mapping = dict(zip(order, slots))
    # Convertir post-minuit
    candidates = sorted(order + [hm])
    # Heuristique simple: choisir le dernier slot qui ne dépasse pas hm
    last = None
    for val in order:
        if val <= hm or (hm < 130 and val == 130):
            last = val
    return mapping.get(last or 900, "09:00")


def _pick_column(df: pd.DataFrame, candidates: List[str]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for name in candidates:
        col = lower_map.get(name.lower())
        if col:
            return col
    return None


def _is_fund_like(name: str) -> bool:
    if not name:
        return False
    return bool(re.search(r"\b(ETF|ETN|TRUST|FUND)\b", name, flags=re.I))


def compute_score_and_tags(row: Dict[str, Any]) -> tuple[int, List[str], str]:
    score = 0
    tags: List[str] = []
    comments_parts: List[str] = []

    # Market Cap
    mc = row.get("MarketCap", 0) or 0
    if MC_MIN <= mc <= 150_000_000:
        score += 30
        tags.append("MC_50-150")
    elif 150_000_000 < mc <= MC_MAX:
        score += 20
        tags.append("MC_150-200")

    # Exchange
    exch = normalize_exchange(row.get("Exchange", ""))
    if exch in PRIORITY_EXCHANGES:
        score += 15
        tags.append("Nasdaq")

    # Sector
    # Normalisation robuste du secteur (évite NaN/float)
    sector_val = row.get("Sector", "")
    sector = str(sector_val if sector_val is not None else "").upper()
    if any(s in sector for s in PRIORITY_SECTORS):
        score += 15
        tags.append("PrioritySector")

    # Price band
    price = float(row.get("Price", 0) or 0)
    if 5.0 <= price <= PREFERRED_PRICE_MAX:
        score += 20
        tags.append("PriceBand5-10")
    elif price >= PRICE_MIN:
        score += 10

    # Volume soft
    vol = int(row.get("Volume", 0) or 0)
    if vol >= VOLUME_SOFT_MIN:
        score += 10
        tags.append("VolAdequate")

    # Data quality (grossière): non fund-like et champs présents
    name = row.get("CompanyName", "")
    if not _is_fund_like(name) and all(k in row for k in ("Ticker", "MarketCap", "Price")):
        score += 10
        tags.append("DataComplete")
        if exch:
            tags.append("NotOTC")

    # Commentaire court
    if exch:
        comments_parts.append(exch)
    if "PrioritySector" in tags:
        comments_parts.append("SectorPriority")
    if "PriceBand5-10" in tags:
        comments_parts.append("PriceBand 5–10")
    if mc:
        comments_parts.append(f"MC {mc/1e6:.0f}M")

    comments = " | ".join(comments_parts)
    return score, tags, comments


def load_input() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)

    ok, msg = validate_csv_columns(
        df.columns,
        [
            # on tolère l’absence de certains champs, ils seront vides
            # mais Ticker, Market Cap, Price, Volume sont fortement souhaités
            # noms candidats ci-dessous
        ],
    )
    # On ne bloque pas; on gère les colonnes de façon tolérante

    # Colonnes candidates
    col_ticker = _pick_column(df, ["Ticker", "symbol"]) or "Ticker"
    col_mc = _pick_column(df, ["Market Cap", "MarketCap", "marketCap"]) or "Market Cap"
    col_price = _pick_column(df, ["Price", "price", "Current Price"]) or "Price"
    col_vol = _pick_column(df, ["Volume", "volume"]) or "Volume"
    col_exch = _pick_column(df, ["Exchange", "Market"]) or "Exchange"
    col_sector = _pick_column(df, ["Sector", "sector"]) or "Sector"
    col_name = _pick_column(df, ["Company Name", "companyName", "Name"]) or "Company Name"

    # Normalisation minimale
    df_out = pd.DataFrame()
    df_out["Ticker"] = df[col_ticker].map(normalize_ticker)
    df_out["MarketCap"] = pd.to_numeric(df.get(col_mc, pd.Series([None] * len(df))), errors="coerce")
    df_out["Price"] = pd.to_numeric(df.get(col_price, pd.Series([None] * len(df))), errors="coerce")
    df_out["Volume"] = pd.to_numeric(df.get(col_vol, pd.Series([0] * len(df))), errors="coerce").fillna(0).astype(int)
    df_out["Exchange"] = df.get(col_exch, pd.Series([None] * len(df)))
    df_out["Sector"] = df.get(col_sector, pd.Series([None] * len(df)))
    df_out["CompanyName"] = df.get(col_name, pd.Series([None] * len(df)))

    return df_out


def filter_and_score(df: pd.DataFrame) -> pd.DataFrame:
    # Filtres « hard »
    base = df[(df["MarketCap"] >= MC_MIN) & (df["MarketCap"] <= MC_MAX) & (df["Price"] >= PRICE_MIN)].copy()

    scores: List[int] = []
    tags_list: List[List[str]] = []
    comments: List[str] = []

    for _, r in base.iterrows():
        s, tg, com = compute_score_and_tags(r.to_dict())
        scores.append(s)
        tags_list.append(tg)
        comments.append(com)

    base["ScorePotential"] = scores
    base["ReasonsTags"] = [";".join(t) for t in tags_list]
    base["Comments"] = comments

    # Seuil recommandé (≥ 60)
    result = base[base["ScorePotential"] >= 60].copy()
    return result


def status_and_changes(df_today: pd.DataFrame) -> pd.DataFrame:
    # Cherche un JSON d’hier si présent pour marquer New/Maintained
    today = datetime.now(ZoneInfo("Europe/Paris")).date()
    prev_json = None
    if os.path.isdir(EVOL_DIR):
        files = [f for f in os.listdir(EVOL_DIR) if f.startswith("extended_to_potential_") and f.endswith(".json")]
        files.sort(reverse=True)
        for f in files:
            if f"_{today}" in f:
                # même jour: on le prend quand même comme référence la plus récente
                prev_json = os.path.join(EVOL_DIR, f)
                break
            else:
                prev_json = os.path.join(EVOL_DIR, f)
                break

    status = []
    change_notes = []
    prev_set = set()
    if prev_json and os.path.isfile(prev_json):
        try:
            with open(prev_json, "r", encoding="utf-8") as f:
                prev = json.load(f)
            prev_items = prev.get("items", [])
            prev_set = {normalize_ticker(it.get("Ticker", "")) for it in prev_items}
        except Exception:
            prev_set = set()

    for _, r in df_today.iterrows():
        t = r["Ticker"]
        if t in prev_set:
            status.append("Maintained")
            change_notes.append("")
        else:
            status.append("New")
            change_notes.append("")

    df_today["Status"] = status
    df_today["ChangeNotes"] = change_notes
    df_today["Date"] = today.isoformat()
    return df_today


def write_outputs(df_out: pd.DataFrame) -> None:
    # CSV courant (atomique)
    tmp = f"{OUTPUT_CSV}.tmp"
    df_out.to_csv(tmp, index=False)
    os.replace(tmp, OUTPUT_CSV)

    # JSON archive du jour (append runs dans un seul fichier par jour)
    paris = datetime.now(ZoneInfo("Europe/Paris"))
    utc_ts = datetime.now(timezone.utc).isoformat()
    run_date = paris.date().isoformat()
    run_time = paris.time().strftime("%H:%M:%S")
    schedule_slot = _choose_schedule_slot(paris)

    archive_path = os.path.join(EVOL_DIR, f"extended_to_potential_{run_date}.json")
    safe_ensure_dir(EVOL_DIR)

    metadata = {
        "pipeline_step": "extended_to_potential",
        "source_csv": os.path.relpath(INPUT_CSV),
        "run_date": run_date,
        "run_time": run_time,
        "schedule_slot": schedule_slot,
        "utc_timestamp": utc_ts,
        "parameters": {
            "mc_min": MC_MIN,
            "mc_max": MC_MAX,
            "price_min": PRICE_MIN,
            "volume_soft": VOLUME_SOFT_MIN,
        },
        "weights": {"mc": 30, "exchange": 15, "sector": 15, "price_band": 20, "volume": 10, "data_quality": 10},
        "version": "1.0",
    }

    counters = {
        "total_input": int(pd.read_csv(INPUT_CSV).shape[0]),
        "filtered": int(df_out.shape[0]),
    }

    # Remplacer NaN/NaT par None pour JSON strict
    df_json = df_out.replace({np.nan: None})
    items = df_json.to_dict(orient="records")

    if os.path.exists(archive_path):
        try:
            current = json.load(open(archive_path, "r", encoding="utf-8"))
        except Exception:
            current = {"metadata": metadata, "runs": []}
    else:
        current = {"metadata": metadata, "runs": []}

    current.setdefault("runs", []).append({
        "run_id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "counters": counters,
        "items": items,
    })

    # Sanitize récursif (remplace NaN/Inf par None) au cas où des runs antérieurs contenaient des NaN
    def _sanitize(obj):
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(v) for v in obj]
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
        return obj

    current = _sanitize(current)
    write_json_atomic(archive_path, current)


def main() -> None:
    lock = acquire_lock("extended_to_potential", timeout_seconds=7200)
    try:
        df = load_input()
        result = filter_and_score(df)
        result = status_and_changes(result)
        write_outputs(result)
        print(f"extended_to_potential.csv écrit ({len(result)} lignes)")
    finally:
        release_lock(lock)


if __name__ == "__main__":
    main()


