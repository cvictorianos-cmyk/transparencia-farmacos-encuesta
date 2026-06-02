"""Configuracion global del proyecto."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# La base de datos SQLite suele fallar en carpetas sincronizadas (OneDrive, Dropbox).
# Por defecto, la DB va a /tmp/benchmarking_oncologico_db (override con env DB_DIR).
# Los exports siguen yendo a BASE_DIR/exports para que el usuario los pueda abrir.
DATA_DIR = Path(os.environ.get("DB_DIR", "/tmp/benchmarking_oncologico_db"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "benchmarking.sqlite"

PLAYWRIGHT_TIMEOUT_MS = 60_000
NAV_TIMEOUT_MS = 45_000
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)
ISP_MAX_PRODUCTS = None
DELAY_BETWEEN_CLINICS_S = 1.0
