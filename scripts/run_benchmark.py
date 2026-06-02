"""Script de línea de comandos: ejecuta el benchmark end-to-end y exporta a JSON+Excel.

Uso:
    python scripts/run_benchmark.py bevacizumab
    python scripts/run_benchmark.py bevacizumab --clinicas santa_maria indisa
"""
import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Permitir ejecutar sin instalar el paquete
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.benchmark import ejecutar_benchmark
from app.export import export_benchmark

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("principio_activo", help="Ej: bevacizumab")
    ap.add_argument("--clinicas", nargs="+", default=None,
                    help="Subset de clínicas (santa_maria indisa alemana uandes davila)")
    ap.add_argument("--marcas-extra", nargs="+", default=None)
    args = ap.parse_args()

    res = await ejecutar_benchmark(
        principio_activo=args.principio_activo,
        clinicas=args.clinicas,
        marcas_extra=args.marcas_extra,
    )
    bench_id = res["benchmark"]["id"]

    print(json.dumps(
        {
            "benchmark_id": bench_id,
            "principio_activo": res["benchmark"]["principio_activo"],
            "total_productos_isp": len(res["productos_isp"]),
            "total_aranceles": len(res["aranceles"]),
        },
        indent=2,
    ))

    json_path = export_benchmark(bench_id, "json")
    xlsx_path = export_benchmark(bench_id, "xlsx")
    print(f"\nExportado:\n  JSON  → {json_path}\n  Excel → {xlsx_path}")


if __name__ == "__main__":
    asyncio.run(main())
