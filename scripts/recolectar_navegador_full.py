"""Recolector con Playwright para UANDES + clínicas SPA.

Ejecutable SOLO en entornos con Playwright disponible (Render, Docker con deps).
NO ejecutar en sandbox local.

Características:
- Captura UANDES por búsquedas automáticas en navegador
- Captura clínicas SPA (Dávila, Santa María, Alemana) con JS renderizado
- Salida: JSON con filas de hoy, listo para mergear con historial

Uso:
  python3 recolectar_navegador_full.py [--export-json ARCHIVO]

Si --export-json se omite, imprime JSON a stdout.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Optional

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: Playwright no instalado. Instala con: pip install playwright", file=sys.stderr)
    print("       Luego: python3 -m playwright install chromium --with-deps", file=sys.stderr)
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_COLS = ["fecha", "clinica", "principio_activo", "glosa", "precio_clp"]

DROGAS = [
    "pembrolizumab", "daratumumab", "nivolumab", "bevacizumab", "rituximab",
    "cetuximab", "ipilimumab",
]

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
    return [pa] + NOMBRES_COMERCIALES.get(pa, [])

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().upper())

def _precio_int(txt) -> Optional[int]:
    if txt is None or txt == "":
        return None
    txt = txt.strip().replace(".", "").replace(",", "")
    try:
        return int(txt)
    except ValueError:
        return None

def _match_droga(glosa: str, pa: str) -> bool:
    pa_norm = _norm(pa)
    return pa_norm in _norm(glosa)

def _dedup(filas: list[dict]) -> list[dict]:
    unicas = []
    visto = set()
    for f in filas:
        key = (f["clinica"], f["principio_activo"], f.get("glosa", ""), f["precio_clp"])
        if key not in visto:
            visto.add(key)
            unicas.append(f)
    return unicas

async def recolectar_uandes(page) -> list[dict]:
    """Busca fármacos en UANDES usando Playwright."""
    filas = []
    for d in DROGAS:
        for term in terminos_busqueda(d):
            url = (f"https://www.clinicauandes.cl/aranceles/resultado"
                   f"?indexCatalogue=aranceles-web&searchQuery={urllib.parse.quote(term)}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=10000)
                await page.wait_for_timeout(500)

                table_html = await page.evaluate("""() => {
                    const table = document.querySelector('table');
                    return table ? table.outerHTML : null;
                }""")

                if table_html and term.upper() in table_html:
                    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
                    for row in rows:
                        tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                        if len(tds) >= 5:
                            codigo = re.sub(r'<[^>]+>', '', tds[0]).strip()
                            glosa = re.sub(r'<[^>]+>', '', tds[2]).strip()
                            precio_txt = re.sub(r'<[^>]+>', '', tds[-1]).strip()
                            precio = _precio_int(precio_txt)

                            if glosa and precio and _match_droga(glosa, d):
                                filas.append({
                                    "clinica": "Clinica Universidad de los Andes",
                                    "principio_activo": d,
                                    "glosa": f"{glosa} ({codigo})" if codigo else glosa,
                                    "precio_clp": precio
                                })
            except Exception as e:
                print(f"  UANDES {term}: {type(e).__name__}", file=sys.stderr, flush=True)

    return _dedup(filas)

async def recolectar_spa(page, clinica_url: str, clinica_nombre: str) -> list[dict]:
    """Captura clínicas SPA con JS renderizado."""
    filas = []
    try:
        await page.goto(clinica_url, wait_until="networkidle", timeout=10000)
        await page.wait_for_timeout(1000)

        page_text = await page.evaluate("() => document.body.innerText")

        for d in DROGAS:
            for term in terminos_busqueda(d):
                if term.lower() in page_text.lower():
                    pattern = rf'{re.escape(term)}\s+[^0-9]*([0-9,.]+)'
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    for match in matches:
                        precio = _precio_int(match)
                        if precio and precio > 100000:
                            filas.append({
                                "clinica": clinica_nombre,
                                "principio_activo": d,
                                "glosa": term.upper(),
                                "precio_clp": precio
                            })
    except Exception as e:
        print(f"  {clinica_nombre}: {type(e).__name__}", file=sys.stderr, flush=True)

    return _dedup(filas)

async def main_async() -> list[dict]:
    """Ejecuta captura con Playwright."""
    todas = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Recolectando UANDES...", file=sys.stderr, flush=True)
        filas_u = await recolectar_uandes(page)
        todas.extend(filas_u)
        print(f"  OK: {len(filas_u)} filas", file=sys.stderr)

        clinicas_spa = [
            ("https://www.clinicadavila.cl", "Clinica Davila"),
            ("https://www.clinicasantamaria.cl", "Clinica Santa Maria"),
            ("https://www.clinicaalemana.cl", "Clinica Alemana"),
        ]

        for url, nombre in clinicas_spa:
            print(f"Recolectando {nombre}...", file=sys.stderr, flush=True)
            filas_s = await recolectar_spa(page, url, nombre)
            todas.extend(filas_s)
            print(f"  OK: {len(filas_s)} filas", file=sys.stderr)

        await browser.close()

    return todas

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-json", default=None)
    args = parser.parse_args()

    filas = asyncio.run(main_async())

    hoy = date.today().isoformat()
    for f in filas:
        f["fecha"] = hoy

    output = json.dumps(filas, ensure_ascii=False, indent=2)
    if args.export_json:
        Path(args.export_json).write_text(output, encoding="utf-8")
        print(f"Exportado a {args.export_json}: {len(filas)} filas", file=sys.stderr)
    else:
        print(output)

    return 0 if filas else 1

if __name__ == "__main__":
    sys.exit(main())
