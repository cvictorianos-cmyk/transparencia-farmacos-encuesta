"""Scraper Clinica Santa Maria. Browser fresco por cada query (mas estable)."""
from __future__ import annotations
import re
from typing import List

from playwright.async_api import async_playwright

from .base import parse_clp


URL = "https://www.clinicasantamaria.cl/aranceles"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)
RE_HABIL = re.compile(r"h[áa]bil[:\s]*\$?\s*([\d\.\,]+)", re.I)


def _extract_habil(cell_text: str):
    if not cell_text:
        return None
    m = RE_HABIL.search(cell_text)
    if m:
        return parse_clp(m.group(1))
    m2 = re.search(r"\$?\s*([\d\.\,]+)", cell_text)
    return parse_clp(m2.group(1)) if m2 else None


class SantaMariaScraper:
    name = "santa_maria"

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def search(self, query: str) -> List[dict]:
        results: list[dict] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless,
                args=["--disable-dev-shm-usage", "--no-sandbox"])
            ctx = await browser.new_context(locale="es-CL", user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800})
            page = await ctx.new_page()
            try:
                await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(2500)
                await page.fill("#txtnp", query)
                # Click Buscar
                try:
                    await page.get_by_role("button", name="Buscar").first.click(timeout=4000)
                except Exception:
                    await page.evaluate(
                        """() => {
                            const b = Array.from(document.querySelectorAll('button'))
                                .find(x => (x.innerText||'').trim().toLowerCase()==='buscar' && x.offsetParent !== null);
                            if (b) b.click();
                        }"""
                    )
                await page.wait_for_timeout(4000)
                rows = await page.evaluate("""() => {
                    const tables = Array.from(document.querySelectorAll('table'));
                    if (!tables.length) return [];
                    const t = tables[tables.length - 1];
                    return Array.from(t.rows).map(r => Array.from(r.cells).map(c => c.innerText.trim()));
                }""")
                if not rows or len(rows) < 2:
                    return []
                header = [c.lower() for c in rows[0]]
                idx_p = next((i for i, h in enumerate(header) if "prest" in h), 0)
                idx_cf = next((i for i, h in enumerate(header) if "fonasa" in h and "cód" in h), 1)
                idx_ci = next((i for i, h in enumerate(header) if "interno" in h), 2)
                idx_part = next((i for i, h in enumerate(header) if "particular" in h), 3)
                idx_fon = next((i for i, h in enumerate(header) if h.strip() == "fonasa"), 4)
                idx_isa = next((i for i, h in enumerate(header) if "isapre" in h), 5)
                for row in rows[1:]:
                    if len(row) < 4:
                        continue
                    nombre = row[idx_p] if idx_p < len(row) else ""
                    if not nombre:
                        continue
                    results.append({
                        "clinica": self.name,
                        "query_busqueda": query,
                        "nombre_prestacion": nombre,
                        "codigo_fonasa": row[idx_cf] if idx_cf < len(row) else None,
                        "codigo_interno": row[idx_ci] if idx_ci < len(row) else None,
                        "precio_particular_clp": _extract_habil(row[idx_part] if idx_part < len(row) else ""),
                        "precio_fonasa_clp": _extract_habil(row[idx_fon] if idx_fon < len(row) else ""),
                        "precio_isapre_clp": _extract_habil(row[idx_isa] if idx_isa < len(row) else ""),
                        "horario": "Habil",
                        "url_origen": URL,
                        "notas": "Precio Habil; Inhabil disponible en celda original.",
                    })
            finally:
                await ctx.close()
                await browser.close()
        return results
