"""Anade resultados de una clinica adicional a un benchmark existente."""
import argparse, asyncio, sys, json, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import database as db
from app.benchmark import _scrape_clinic
from scrapers import ISPChileScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("benchmark_id", type=int)
    ap.add_argument("clinica")
    args = ap.parse_args()

    data = db.obtener_benchmark(args.benchmark_id)
    if not data:
        print(f"Benchmark {args.benchmark_id} no existe", file=sys.stderr); sys.exit(1)

    productos = data["productos_isp"]
    marcas = ISPChileScraper.marcas_unicas(productos)
    print(f"Benchmark {args.benchmark_id}: principio={data['benchmark']['principio_activo']}, marcas={marcas}", flush=True)

    ars = await _scrape_clinic(args.clinica, marcas)
    if ars:
        db.guardar_aranceles(args.benchmark_id, ars)
    db.actualizar_totales(args.benchmark_id)
    print(f"Anadidos {len(ars)} aranceles de {args.clinica} al benchmark {args.benchmark_id}")

asyncio.run(main())
