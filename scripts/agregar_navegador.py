#!/usr/bin/env python3
"""Fusiona al historial las filas de las clinicas capturadas por NAVEGADOR
(UANDES, Davila, Santa Maria, Alemana), que no son viables por httpx (DataDome /
Azure WAF). El agente del lunes navega cada sitio, extrae precio particular por
farmaco y arma un JSON; este script lo fusiona de forma idempotente (reemplaza
las filas de hoy solo de las clinicas presentes en el JSON).

Formato JSON (lista de objetos):
  [{"clinica":"Clinica Davila","principio_activo":"rituximab",
    "glosa":"RITUXIMAB 500 MG/50 ML (MABTHERA)","precio_clp":1093275}, ...]

Reglas de captura (resumen; detalle en la memoria del proyecto):
  - UANDES  https://www.clinicauandes.cl/aranceles/resultado?indexCatalogue=aranceles-web&searchQuery=<INN>
            precio = ARANCEL PARTICULAR (ultima columna).
  - Alemana https://www.clinicaalemana.cl/aranceles/buscar?q=<INN o marca>
            precio = "Valor paciente particular".
  - Davila  https://www.davila.cl/aranceles  (sucursal "Clinica Davila"), pestana AMBULATORIO.
  - Sta.Maria https://www.clinicasantamaria.cl/aranceles , pestana OTROS.
  Filtrar glosas placeholder CENABAST/LRS (precio < 10000) y jeringas
  intravitreas de bevacizumab (dejar solo viales oncologicos).

Uso:  python scripts/agregar_navegador.py <ruta_json>
"""
import sys, csv, json
from datetime import date
sys.path.insert(0, "scripts")
import recolectar_diario as r

CLINICAS_NAV = {"Clinica Universidad de los Andes", "Clinica Davila",
                "Clinica Santa Maria", "Clinica Alemana"}

def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: agregar_navegador.py <ruta_json>", file=sys.stderr); return 2
    hoy = date.today().isoformat()
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    nuevas = []; clinicas = set()
    for row in data:
        cl = row["clinica"]; precio = int(row["precio_clp"])
        if cl not in CLINICAS_NAV:
            print(f"  aviso: clinica no esperada '{cl}', se omite", file=sys.stderr); continue
        if precio < 10000:  # descarta placeholders CENABAST/LRS
            continue
        nuevas.append({"fecha": hoy, "clinica": cl,
                       "principio_activo": row["principio_activo"],
                       "glosa": row["glosa"], "precio_clp": precio})
        clinicas.add(cl)
    if not nuevas:
        print("Sin filas validas en el JSON.", file=sys.stderr); return 1
    existentes = []
    if r.CSV_PATH.exists():
        with r.CSV_PATH.open(encoding="utf-8") as fh: existentes = list(csv.DictReader(fh))
    existentes = [x for x in existentes if not (x["fecha"] == hoy and x["clinica"] in clinicas)]
    with r.CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=r.CSV_COLS); w.writeheader(); w.writerows(existentes); w.writerows(nuevas)
    resumen = {}
    for f in nuevas: resumen[f["clinica"]] = resumen.get(f["clinica"], 0) + 1
    print(f"OK navegador: {len(nuevas)} filas para {hoy}; " +
          ", ".join(f"{k}={v}" for k, v in sorted(resumen.items())))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
