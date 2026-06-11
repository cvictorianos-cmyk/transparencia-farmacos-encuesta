"""Recolector diario de precios de farmacos oncologicos.

Descarga el valor particular publicado por cada clinica (sin navegador, solo
HTTP) y agrega las filas del dia a data/historial_precios.csv para construir
la linea de tiempo de precios del comparador (version Premium).

Fuentes (las mismas del catalogo):
    - Clinica INDISA ............... GraphQL publico ng-backend.indisa.cl
    - Clinica U. de los Andes ...... pagina de resultados (tabla HTML)
    - UC Marcoleta (Hospital Clinico) . API publica aranceles.ucchristus.cl (centroId=1)
    - UC San Carlos (Apoquindo) ...... API publica aranceles.ucchristus.cl (centroId=3)
    - Clinica Davila, Clinica Santa Maria, Clinica Alemana y FALP: sus aranceles
      no exponen un endpoint HTTP simple (Davila/Santa Maria/Alemana son SPAs
      JavaScript; FALP publica solo PDF), por lo que no se recolectan aqui; sus
      precios se mantienen con el ultimo valor conocido del catalogo. Para
      actualizarlos se revisa manualmente y se edita app/catalogo.py.

Uso:  python scripts/recolectar_diario.py
Idempotente: si ya hay filas con la fecha de hoy, no duplica.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import urllib.parse
from datetime import date
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "historial_precios.csv"
CSV_COLS = ["fecha", "clinica", "principio_activo", "glosa", "precio_clp"]

DROGAS = [
    "pembrolizumab", "daratumumab", "nivolumab", "bevacizumab", "rituximab",
    "cetuximab", "ipilimumab",
]

# Para cada principio activo, ademas se busca por nombre comercial (marca
# innovadora y biosimilares), porque algunas clinicas indexan por uno u otro.
NOMBRES_COMERCIALES = {
    "pembrolizumab": ["keytruda"],
    "daratumumab": ["darzalex"],
    "nivolumab": ["opdivo"],
    "bevacizumab": ["avastin", "abxeda", "mvasi", "zirabev", "krabeva", "bemabix", "vegzelma"],
    "rituximab": ["mabthera", "truxima", "rixathon", "reditux", "ritemvia"],
    "cetuximab": ["erbitux"],
    "ipilimumab": ["yervoy"],
}


def terminos_busqueda(pa: str) -> list[str]:
    """Principio activo + sus nombres comerciales (para barrer ambos)."""
    return [pa] + NOMBRES_COMERCIALES.get(pa, [])


HEADERS = {"User-Agent": "Mozilla/5.0 (proyecto academico MSIIN - benchmarking precios)"}
TIMEOUT = 30.0


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().upper())


def _precio_int(txt) -> int | None:
    if txt is None:
        return None
    if isinstance(txt, (int, float)):
        return int(txt)
    digits = re.sub(r"[^\d]", "", str(txt))
    return int(digits) if digits else None


def _match_droga(glosa: str, pa: str) -> bool:
    """True si la glosa corresponde al principio activo o a una de sus marcas."""
    g = _norm(glosa)
    if pa.upper()[:6] in g:
        return True
    return any(nc.upper() in g for nc in NOMBRES_COMERCIALES.get(pa, []))


def _dedup(filas: list[dict]) -> list[dict]:
    vistos, unicas = set(), []
    for f in filas:
        k = (f["clinica"], f["glosa"], f["precio_clp"])
        if k not in vistos:
            vistos.add(k)
            unicas.append(f)
    return unicas


def recolectar_indisa(client: httpx.Client) -> list[dict]:
    filas = []
    sha = "bf0f817f735780b095df216d3b3d06545663e99c66ca98a7e58b02577c9d48e2"

    def buscar(obj):
        if isinstance(obj, dict):
            if isinstance(obj.get("landingAranceles"), list):
                return obj["landingAranceles"]
            for v in obj.values():
                f = buscar(v)
                if f:
                    return f
        return None

    for d in DROGAS:
        # barrer principio activo y nombres comerciales
        for term in terminos_busqueda(d):
            variables = urllib.parse.quote(json.dumps({
                "param": "medicamentos", "araprev": "particular", "aracode": "",
                "araname": term, "uri": "/aranceles-buscador/"}))
            ext = urllib.parse.quote(json.dumps(
                {"persistedQuery": {"version": 1, "sha256Hash": sha}}))
            url = (f"https://ng-backend.indisa.cl/wp/index.php?graphql"
                   f"&operationName=GetPageData&variables={variables}&extensions={ext}")
            try:
                r = client.get(url)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"  INDISA {term}: ERROR {e}", file=sys.stderr)
                continue
            for a in (buscar(data) or []):
                glosa = _norm(a.get("service_detail"))
                precio = _precio_int(a.get("med_value"))
                if glosa and precio and _match_droga(glosa, d):
                    filas.append({"clinica": "Clinica INDISA",
                                  "principio_activo": d, "glosa": glosa, "precio_clp": precio})
    return _dedup(filas)


def recolectar_uandes(client: httpx.Client) -> list[dict]:
    filas = []
    for d in DROGAS:
        for term in terminos_busqueda(d):
            url = ("https://www.clinicauandes.cl/aranceles/resultado"
                   f"?indexCatalogue=aranceles-web&searchQuery={urllib.parse.quote(term)}")
            try:
                r = client.get(url)
                r.raise_for_status()
                html = r.text
            except Exception as e:
                print(f"  UANDES {term}: ERROR {e}", file=sys.stderr)
                continue
            # filas de tabla: ... | CODIGO | NOMBRE | - | - | 1.234.567 | 1.234.567
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
                celdas = [re.sub(r"<[^>]+>", " ", c) for c in
                          re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
                celdas = [_norm(c) for c in celdas]
                joined = " ".join(celdas)
                if len(celdas) >= 6 and _match_droga(joined, d):
                    nombre = next((c for c in celdas if _match_droga(c, d)), None)
                    precios = [_precio_int(c) for c in celdas if re.match(r"^[\d.,]+$", c or "")]
                    precios = [p for p in precios if p and p > 10000]
                    if nombre and precios:
                        filas.append({"clinica": "Clinica Universidad de los Andes",
                                      "principio_activo": d, "glosa": nombre,
                                      "precio_clp": precios[-1]})
    return _dedup(filas)


def recolectar_uc(client: httpx.Client) -> list[dict]:
    filas = []
    centros = {1: "UC Marcoleta", 3: "UC San Carlos"}
    for cid, cname in centros.items():
        for d in DROGAS:
            for term in terminos_busqueda(d):
                url = ("https://aranceles.ucchristus.cl/api/public/aranceles/v2"
                       f"?centroId={cid}&query={urllib.parse.quote(term)}&limit=50")
                try:
                    r = client.get(url)
                    r.raise_for_status()
                    data = r.json()
                except Exception as e:
                    print(f"  UC c{cid} {term}: ERROR {e}", file=sys.stderr)
                    continue
                items = data.get("items") or data.get("data") or data.get("results") or []
                for i in items if isinstance(items, list) else []:
                    glosa = _norm(i.get("glosa") or i.get("descripcion"))
                    cod = i.get("codigo")
                    precio = _precio_int(i.get("valor_lista_particular_red"))
                    # solo farmacos (excluir honorarios/procedimientos)
                    tipo = (i.get("tipo") or "").upper()
                    if glosa and precio and _match_droga(glosa, d) and "FARMACO" in (tipo or "FARMACO"):
                        filas.append({"clinica": cname, "principio_activo": d,
                                      "glosa": f"{glosa} ({cod})" if cod else glosa,
                                      "precio_clp": precio})
    return _dedup(filas)


def main() -> int:
    hoy = date.today().isoformat()
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    existentes: list[dict] = []
    if CSV_PATH.exists():
        with CSV_PATH.open(encoding="utf-8") as fh:
            existentes = list(csv.DictReader(fh))
    if any(r["fecha"] == hoy for r in existentes):
        print(f"Ya existen filas para {hoy}; nada que hacer.")
        return 0

    nuevas: list[dict] = []
    with httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        print("Recolectando INDISA...")
        nuevas += recolectar_indisa(client)
        print("Recolectando U. de los Andes...")
        nuevas += recolectar_uandes(client)
        print("Recolectando UC CHRISTUS (x2 centros)...")
        nuevas += recolectar_uc(client)

    if not nuevas:
        print("ADVERTENCIA: no se recolecto ningun precio (¿sitios caidos?).", file=sys.stderr)
        return 1

    for f in nuevas:
        f["fecha"] = hoy

    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLS)
        w.writeheader()
        w.writerows(existentes)
        w.writerows(nuevas)

    print(f"OK: {len(nuevas)} precios guardados para {hoy} en {CSV_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
