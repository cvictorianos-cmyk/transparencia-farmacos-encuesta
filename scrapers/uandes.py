"""Scraper Clinica UAndes. Browser fresco por cada query."""
from __future__ import annotations
from typing import List
from urllib.parse import quote_plus

from playwright.async_api import async_playwright

from .base import parse_clp


URL_TPL = ("https://www.clinicauandes.cl/aranceles/resultado?"
           "indexCatalogue=aranceles-web&searchQuery={q}&wordsMode=AllWords")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"


class UAndesScraper:
    name = "uandes"

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def search(self, query: str) -> List[dict]:
        results: list[dict] = []
        url = URL_TPL.format(q=quote_plus(query))
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless,
                args=["--disable-dev-shm-usage", "--no-sandbox"])
            ctx = await browser.new_context(locale="es-CL", user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800})
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(2500)
                rows = await page.evaluate("""() => {
                    const tables = Array.from(document.querySelectorAll('table'));
                    if (!tables.length) return [];
                    let best = tables[0]; let bestN = best.rows.length;
                    for (const t of tables) { if (t.rows.length > bestN) { best = t; bestN = t.rows.length; } }
                    return Array.from(best.rows).map(r => Array.from(r.cells).map(c => c.innerText.trim()));
                }""")
                if not rows or len(rows) < 2:
                    return []
                for r in rows:
                    joined = " | ".join(r).lower()
                    if "horario hábil" in joined or joined.strip(" |") in {"amb", "hosp", "amb | hosp"}:
                        continue
                    if r and r[0].lower().startswith("código"):
                        continue
                    if len(r) < 3:
                        continue
                    idx_nombre = None
                    for i, c in enumerate(r[:5]):
                        if len(c) > 8 and any(ch.isalpha() for ch in c):
                            idx_nombre = i; break
                    if idx_nombre is None:
                        continue
                    nombre = r[idx_nombre]
                    if query.lower() not in nombre.lower():
                        continue
                    cod_fonasa = r[0] if idx_nombre >= 1 and r[0] and r[0] != "-" else None
                    cod_cuandes = r[1] if idx_nombre >= 2 and r[1] and r[1] != "-" else None
                    precios = r[idx_nombre+1: idx_nombre+5]
                    isa_amb = parse_clp(precios[0]) if len(precios) > 0 else None
                    isa_hosp = parse_clp(precios[1]) if len(precios) > 1 else None
                    part_amb = parse_clp(precios[2]) if len(precios) > 2 else None
                    part_hosp = parse_clp(precios[3]) if len(precios) > 3 else None
                    results.append({
                        "clinica": self.name,
                        "query_busqueda": query,
                        "nombre_prestacion": nombre,
                        "codigo_fonasa": cod_fonasa,
                        "codigo_interno": cod_cuandes,
                        "precio_particular_clp": part_amb if part_amb is not None else part_hosp,
                        "precio_isapre_clp": isa_amb if isa_amb is not None else isa_hosp,
                        "precio_fonasa_clp": None,
                        "horario": "Habil",
                        "url_origen": url,
                        "notas": f"Particular AMB={part_amb} HOSP={part_hosp}; Isapre AMB={isa_amb} HOSP={isa_hosp}",
                    })
            finally:
                await ctx.close()
                await browser.close()
        return results
