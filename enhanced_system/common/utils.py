import os
import json
import time
import errno
from typing import Iterable, Dict, Any, Tuple


def validate_csv_columns(actual_columns: Iterable[str], required_columns: Iterable[str]) -> Tuple[bool, str]:
    """
    Vérifie que toutes les colonnes requises sont présentes dans un CSV.
    Retourne (ok, message).
    """
    actual = set(map(str, actual_columns))
    required = set(map(str, required_columns))
    missing = sorted(required - actual)
    if missing:
        return False, f"Colonnes manquantes: {', '.join(missing)}"
    return True, "OK"


def validate_json_record(record: Dict[str, Any], required_keys: Iterable[str]) -> Tuple[bool, str]:
    """
    Vérifie que les clés critiques existent dans un enregistrement JSON.
    Retourne (ok, message).
    """
    missing = [k for k in required_keys if k not in record or record.get(k) in (None, "")]
    if missing:
        return False, f"Clés manquantes ou vides: {', '.join(missing)}"
    return True, "OK"


EXCHANGE_MAP = {
    "NASDAQ": "NASDAQ",
    "NASD": "NASDAQ",
    "NYSE": "NYSE",
    "AMEX": "AMEX",
    "NYSE MKT": "AMEX",
}


def normalize_ticker(ticker: str) -> str:
    """Uppercase + trim basique."""
    return (ticker or "").strip().upper()


def normalize_exchange(exchange: str) -> str:
    """Mappe quelques variantes fréquentes vers {NASDAQ, NYSE, AMEX}."""
    key = (exchange or "").strip().upper()
    return EXCHANGE_MAP.get(key, key)


def safe_ensure_dir(path: str) -> None:
    """Crée un dossier si nécessaire (idempotent)."""
    os.makedirs(path, exist_ok=True)


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: str, data: Any) -> None:
    """Écrit un JSON de manière atomique (tmp + rename)."""
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


# -------- Locks simples (file-based) ---------
LOCKS_DIR = os.path.join("enhanced_system", "data", "locks")


def acquire_lock(lock_name: str, timeout_seconds: int = 3600, poll_seconds: float = 1.0) -> str:
    """
    Acquire un verrou fichier exclusif (création atomique). Attend jusqu'à timeout.
    Retourne le chemin du lock à utiliser ensuite dans release_lock().
    """
    safe_ensure_dir(LOCKS_DIR)
    lock_path = os.path.join(LOCKS_DIR, f"{lock_name}.lock")
    start = time.time()
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            return lock_path
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            if time.time() - start > timeout_seconds:
                raise TimeoutError(f"Timeout acquisition lock: {lock_name}")
            time.sleep(poll_seconds)


def release_lock(lock_path: str) -> None:
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
    except Exception:
        pass


