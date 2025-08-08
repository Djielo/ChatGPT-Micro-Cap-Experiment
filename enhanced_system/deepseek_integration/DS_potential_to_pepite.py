import os
import sys
import json
import time
import math
import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import argparse

# Rendre importable le paquet racine quand on exécute ce script directement
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from enhanced_system.common.utils import safe_ensure_dir, write_json_atomic, acquire_lock, release_lock
from enhanced_system.deepseek_integration.config import (
    RATE_LIMIT_DELAY,
    DS_CACHE_DIR,
)

# Import de l'analyseur DeepSeek
from enhanced_system.deepseek_integration.deepseek_microcap_analyzer import (
    DeepSeekMicroCapAnalyzer,
)


# =========================
# Configuration
# =========================

DATA_DIR = "enhanced_system/data"
EVOL_DIR = os.path.join(DATA_DIR, "evolution")

INPUT_CSV = os.path.join(DATA_DIR, "extended_to_potential.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "potential_to_pepite.csv")


def _choose_schedule_slot(paris_dt: datetime) -> str:
    slots = ["09:00", "14:30", "18:00", "22:00", "01:30"]
    order = [900, 1430, 1800, 2200, 130]
    hm = int(paris_dt.strftime("%H%M"))
    last = 900
    for val in order:
        if (val == 130 and hm < 130) or (val <= hm and val != 130):
            last = val
    mapping = {900: "09:00", 1430: "14:30", 1800: "18:00", 2200: "22:00", 130: "01:30"}
    return mapping.get(last, "09:00")


def _build_ticker_payload(row: pd.Series) -> Dict[str, Any]:
    return {
        "ticker": str(row.get("Ticker", "")).upper(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "price_at_analysis": float(row.get("Price", 0) or 0),
        "price_7d_before": float(row.get("Price", 0) or 0),  # inconnu ici
        "price_change_pct": 0.0,
        "market_cap": float(row.get("MarketCap", row.get("Market Cap", 0)) or 0),
        "sector": row.get("Sector", "Unknown") or "Unknown",
        "industry": row.get("Industry", "Unknown") or "Unknown",
        "volume_avg_7d": int(row.get("Volume", 0) or 0),  # proxy simple
        "volume_current": int(row.get("Volume", 0) or 0),
        "pe_ratio": None,
        "beta": None,
        "short_ratio": None,
        "cash_per_share": 0.0,  # éviter l'erreur de formatage : .2f sur None
        "debt_to_equity": None,
    }


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


def _load_input() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)
    # Harmoniser quelques colonnes
    if "Market Cap" in df.columns and "MarketCap" not in df.columns:
        df = df.rename(columns={"Market Cap": "MarketCap"})
    return df


def _cache_path(ticker: str, run_date: str, schedule_slot: str) -> str:
    safe_ensure_dir(DS_CACHE_DIR)
    d = os.path.join(DS_CACHE_DIR, run_date, schedule_slot.replace(":", ""))
    safe_ensure_dir(d)
    return os.path.join(d, f"{ticker}.json")


def _from_cache(ticker: str, run_date: str, schedule_slot: str) -> Dict[str, Any] | None:
    path = _cache_path(ticker, run_date, schedule_slot)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _to_cache(ticker: str, run_date: str, schedule_slot: str, data: Dict[str, Any]) -> None:
    path = _cache_path(ticker, run_date, schedule_slot)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_sanitize(data), f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def run_step(limit: int | None = None, only_new: bool = False, force_refresh: bool = False) -> None:
    lock = acquire_lock("DS_potential_to_pepite", timeout_seconds=14400)
    try:
        df = _load_input()

    # Sous-échantillonnage optionnel
    if only_new and "Status" in df.columns:
        df = df[df["Status"].fillna("").str.upper() == "NEW"]
    if limit is not None and limit > 0:
        # Prioriser les meilleurs ScorePotential si dispo
        if "ScorePotential" in df.columns:
            df = df.sort_values("ScorePotential", ascending=False).head(limit)
        else:
            df = df.head(limit)

    analyzer = DeepSeekMicroCapAnalyzer()

    paris = datetime.now(ZoneInfo("Europe/Paris"))
    utc_ts = datetime.now(timezone.utc).isoformat()
    run_date = paris.date().isoformat()
    run_time = paris.time().strftime("%H:%M:%S")
    schedule_slot = _choose_schedule_slot(paris)

    results: List[Dict[str, Any]] = []
    rows_for_csv: List[Dict[str, Any]] = []

    # Itération séquentielle (rate-limit conservateur)
    total = len(df)
    done = 0
    for _, row in df.iterrows():
        ticker = str(row.get("Ticker", "")).upper()
        if not ticker:
            continue

        cached = _from_cache(ticker, run_date, schedule_slot)
        if cached and not force_refresh:
            analysis = cached
        else:
            payload = _build_ticker_payload(row)
            analysis = analyzer.analyze_microcap_with_deepseek.__wrapped__(analyzer, payload) if hasattr(analyzer.analyze_microcap_with_deepseek, "__wrapped__") else None
            if analysis is None:
                # méthode normale (coroutine) attendue
                import asyncio

                async def _one():
                    return await analyzer.analyze_microcap_with_deepseek(payload)

                analysis = asyncio.run(_one())
            _to_cache(ticker, run_date, schedule_slot, analysis)
            # Attente rate-limit + jitter léger
            time.sleep(max(0.0, RATE_LIMIT_DELAY) + random.uniform(0.05, 0.25))

        results.append(analysis)
        done += 1
        print(f"[{done}/{total}] {ticker} analysé", flush=True)

        # Extraire les champs pour le CSV
        input_data = analysis.get("input_data", {})
        ds = analysis.get("deepseek_analysis", {})
        qc = analysis.get("quality_check", {})
        api_stats = analysis.get("api_stats", {})

        rows_for_csv.append({
            "Ticker": ticker,
            "Market Cap": float(row.get("MarketCap", 0) or 0),
            "Price": float(row.get("Price", 0) or 0),
            "Volume": int(row.get("Volume", 0) or 0),
            "Sector": row.get("Sector", None),
            "Market": row.get("Exchange", row.get("Market", None)),
            "ScorePotential": row.get("ScorePotential", None),
            "ReasonsTags": row.get("ReasonsTags", None),
            "Comments": row.get("Comments", None),
            "Status": row.get("Status", None),
            "Date": row.get("Date", run_date),
            "DS_Decision": ds.get("decision"),
            "DS_Confidence": ds.get("confidence"),
            "DS_TargetPrice15d": ds.get("target_price_15j"),
            "DS_Thesis": ds.get("thesis"),
            "DS_Risks": ";".join(ds.get("risk_factors", []) if isinstance(ds.get("risk_factors"), list) else [str(ds.get("risk_factors", ""))]),
            "DS_Catalyseurs": ";".join(ds.get("catalyseurs", []) if isinstance(ds.get("catalyseurs"), list) else [str(ds.get("catalyseurs", ""))]),
            "DS_Conviction": ds.get("conviction_level"),
            "MeetsCriteria": qc.get("meets_criteria"),
            "DS_ConfidenceRequired_Base": qc.get("confidence_required_base"),
            "DS_ConfidenceRequired_Flexible": qc.get("confidence_required_flexible"),
            "DS_Tokens": api_stats.get("tokens_used"),
            "DS_Timestamp": api_stats.get("timestamp"),
        })

    # Ecriture CSV (atomique)
    df_out = pd.DataFrame(rows_for_csv)
    df_out.replace({np.nan: None}, inplace=True)
    tmp = f"{OUTPUT_CSV}.tmp"
    df_out.to_csv(tmp, index=False)
    os.replace(tmp, OUTPUT_CSV)

    # JSON archive du jour
    archive_path = os.path.join(EVOL_DIR, f"potential_to_pepite_{run_date}.json")
    safe_ensure_dir(EVOL_DIR)

    metadata = {
        "pipeline_step": "potential_to_pepite",
        "source_csv": os.path.relpath(INPUT_CSV),
        "run_date": run_date,
        "run_time": run_time,
        "schedule_slot": schedule_slot,
        "utc_timestamp": utc_ts,
        "version": "1.0",
    }

    counters = {
        "total_input": int(len(df)),
        "accepted": int(sum(1 for r in results if r.get("quality_check", {}).get("meets_criteria"))),
        "tokens_used": int(sum(r.get("api_stats", {}).get("tokens_used", 0) for r in results)),
    }

    items = _sanitize(results)

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

    write_json_atomic(archive_path, current)

        print(f"potential_to_pepite.csv écrit ({len(df_out)} lignes)")
    finally:
        release_lock(lock)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Étape 2 — DeepSeek potential → pépite")
    parser.add_argument("--limit", type=int, default=int(os.getenv("DS_PEPITE_LIMIT", "10")), help="Nombre de tickers à traiter (démo)")
    parser.add_argument("--only-new", action="store_true", help="Ne traiter que les entrées avec Status=New si disponible")
    parser.add_argument("--force-refresh", action="store_true", help="Ignorer le cache et réanalyser les tickers")
    args = parser.parse_args()

    run_step(limit=args.limit, only_new=args.only_new, force_refresh=args.force_refresh)


