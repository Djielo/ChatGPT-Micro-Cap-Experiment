import os
import sys
import json
import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any

import numpy as np
import pandas as pd

# Chemin racine importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from enhanced_system.common.utils import safe_ensure_dir, write_json_atomic, acquire_lock, release_lock


DATA_DIR = "enhanced_system/data"
EVOL_DIR = os.path.join(DATA_DIR, "evolution")

INPUT_CSV = os.path.join(DATA_DIR, "potential_to_pepite.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "pepite_to_sharpratio.csv")


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


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


def _expected_return(row: pd.Series) -> float:
    price = float(row.get("Price", 0) or 0)
    target = row.get("DS_TargetPrice15d", None)
    if price <= 0 or target is None or pd.isna(target):
        return 0.0
    return float(target - price) / float(max(price, 1e-6))


def _short_squeeze_factor(row: pd.Series) -> float:
    sr = row.get("ShortRatio", row.get("shortRatio", None))
    fs = row.get("FloatShortPct", None)
    vals = []
    if sr is not None and not pd.isna(sr):
        vals.append(min(1.0, max(0.0, float(sr) / 20.0)))
    if fs is not None and not pd.isna(fs):
        vals.append(min(1.0, max(0.0, float(fs) / 30.0)))
    if not vals:
        return 0.0
    return float(sum(vals) / len(vals))


def _volatility_proxy(row: pd.Series) -> float:
    # Proxy conservateur si pas d'historique: microcaps 30j ~ 8–15% typiquement
    price = float(row.get("Price", 0) or 0)
    mc = float(row.get("Market Cap", row.get("MarketCap", 0)) or 0)
    base = 0.10
    # Légère baisse de vol si MC proche de 200M, hausse si proche de 50M
    if mc > 0:
        scale = (200_000_000 - min(max(mc, 50_000_000), 200_000_000)) / 150_000_000
        base = 0.08 + 0.07 * scale  # 0.08 → 0.15
    if price < 5:
        base = max(base, 0.12)
    return float(min(0.30, max(0.05, base)))


def run_step() -> None:
    lock = acquire_lock("DS_pepite_to_sharpratio", timeout_seconds=7200)
    try:
        df = pd.read_csv(INPUT_CSV)

    if "MarketCap" in df.columns and "Market Cap" not in df.columns:
        df = df.rename(columns={"MarketCap": "Market Cap"})

    paris = datetime.now(ZoneInfo("Europe/Paris"))
    utc_ts = datetime.now(timezone.utc).isoformat()
    run_date = paris.date().isoformat()
    run_time = paris.time().strftime("%H:%M:%S")
    schedule_slot = _choose_schedule_slot(paris)

    # Calculs
    df["ExpectedReturn15d"] = df.apply(_expected_return, axis=1)
    df["ShortSqueezeFactor"] = df.apply(_short_squeeze_factor, axis=1)
    df["Volatility30d"] = df.apply(_volatility_proxy, axis=1)

    conf = df.get("DS_Confidence", pd.Series([0.0] * len(df))).fillna(0).astype(float)
    ret15 = df["ExpectedReturn15d"].fillna(0).astype(float)
    vol30 = df["Volatility30d"].replace(0, 1e-6).astype(float)
    ssf = (1.0 + 0.3 * df["ShortSqueezeFactor"].fillna(0).astype(float))

    df["DS_SharpRatio"] = (ret15 * conf * ssf) / vol30

    # Tri final (confiance > ratio)
    if "DS_Confidence" in df.columns:
        df = df.sort_values(["DS_Confidence", "DS_SharpRatio"], ascending=[False, False]).reset_index(drop=True)
    else:
        df = df.sort_values(["DS_SharpRatio"], ascending=[False]).reset_index(drop=True)

    # Écriture CSV
    tmp = f"{OUTPUT_CSV}.tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, OUTPUT_CSV)

    # Archive JSON
    archive_path = os.path.join(EVOL_DIR, f"pepite_to_sharpratio_{run_date}.json")
    safe_ensure_dir(EVOL_DIR)

    metadata = {
        "pipeline_step": "pepite_to_sharpratio",
        "source_csv": os.path.relpath(INPUT_CSV),
        "run_date": run_date,
        "run_time": run_time,
        "schedule_slot": schedule_slot,
        "utc_timestamp": utc_ts,
        "version": "1.0",
    }

    counters = {
        "total_input": int(len(df)),
    }

    items = _sanitize(df.to_dict(orient="records"))

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

    print(f"pepite_to_sharpratio.csv écrit ({len(df)} lignes)")
    finally:
        release_lock(lock)


if __name__ == "__main__":
    run_step()


