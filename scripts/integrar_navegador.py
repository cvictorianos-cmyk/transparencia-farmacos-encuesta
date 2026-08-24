"""Integra JSON de recolector Playwright con CSV histórico.

Uso:
  python3 integrar_navegador.py <archivo_json>

Lee el JSON del recolectar_navegador_full.py y lo agrega al histórico,
evitando duplicados e idempotencia (no duplica si ya existen filas del día).
"""
import sys
import csv
import json
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "historial_precios.csv"
CSV_COLS = ["fecha", "clinica", "principio_activo", "glosa", "precio_clp"]

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 integrar_navegador.py <archivo_json>", file=sys.stderr)
        return 1

    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"ERROR: {json_file} no existe", file=sys.stderr)
        return 1

    # Lee JSON
    try:
        nuevas = json.loads(json_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR leyendo JSON: {e}", file=sys.stderr)
        return 1

    if not nuevas:
        print("JSON vacío", file=sys.stderr)
        return 1

    hoy = date.today().isoformat()
    print(f"Integrando {len(nuevas)} filas para {hoy}", file=sys.stderr, flush=True)

    # Lee CSV existente
    existentes = []
    if CSV_PATH.exists():
        with CSV_PATH.open(encoding="utf-8") as fh:
            existentes = list(csv.DictReader(fh))

    # Chequea idempotencia
    if any(r["fecha"] == hoy for r in existentes):
        print(f"Ya existen filas para {hoy}; no se sobrescribe", file=sys.stderr)
        return 0

    # Escribe CSV (existentes + nuevas)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLS)
        w.writeheader()
        w.writerows(existentes)
        w.writerows(nuevas)

    print(f"OK: {len(nuevas)} filas integradas en {CSV_PATH.name}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
