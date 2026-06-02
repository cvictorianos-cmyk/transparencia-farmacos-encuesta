"""Scraper para Clínica Alemana.

URL: https://www.clinicaalemana.cl/aranceles/list/insumos-y-medicamentos
Tecnología: SPA (CSS modules con clases tipo `_page_xxxxx`).

Por defecto la página muestra TODOS los insumos y medicamentos paginados (1915 páginas).
Estrategia: usar el placeholder "Buscar arancel..." para filtrar.

Columnas reportadas:
  Prestación | Código interno | Código Fonasa | Valor particular | Valor Fonasa | Valor Isapre
"""
from __future__ import annotations
from typing import List

from .base import ScraperBase, parse_clp


URL = "https://www.clinicaalemana.cl/aranceles/list/insumos-y-medicamentos"


class AlemanaScraper(ScraperBase):
    name = "alemana"
    base_url = URL

    async def search(self, query: str) -> List[dict]:
        page = await self.new_page()
        results: list[dict] = []
        try:
            await page.goto(URL, wait_until="networkidle", timeout=self.timeout_ms)
            await page.wait_for_timeout(3_000)
            # Llenar input "Buscar arancel..."
            try:
                await page.get_by_placeholder("Buscar arancel...").fill(query)
            except Exception:
                # Fallback: primer input visible de tipo text
                await page.locator("input").first.fill(query)
            # Click botón Buscar
            try:
                await page.get_by_role("button", name="Buscar").first.click(timeout=4_000)
            except Exception:
                # Algunos render usan press Enter
                try:
                    await page.get_by_placeholder("Buscar arancel...").press("Enter")
                except Exception:
                    pass
            await page.wait_for_timeout(6_000)

            # Extraer datos. La estructura puede ser table o divs con role="row"/"cell".
            rows = await page.evaluate(
                """() => {
                    let rows = [];
                    const tables = Array.from(document.querySelectorAll('table'));
                    if (tables.length) {
                        const t = tables[tables.length - 1];
                        rows = Array.from(t.rows).map(r => Array.from(r.cells).map(c => c.innerText.trim()));
                    }
                    if (rows.length < 2) {
                        // Buscar divs con role row/cell
                        const dRows = Array.from(document.querySelectorAll('[role="row"]'));
                        if (dRows.length) {
                            rows = dRows.map(r => Array.from(r.querySelectorAll('[role="cell"], [role="columnheader"]'))
                                .map(c => c.innerText.trim()));
                        }
                    }
                    return rows;
                }"""
            )

            if not rows or len(rows) < 2:
                return []

            header = [c.lower() for c in rows[0]]
            idx_pres = next((i for i, h in enumerate(header) if "prest" in h or "nombre" in h or "descrip" in h), 0)
            idx_int = next((i for i, h in enumerate(header) if "interno" in h), 1)
            idx_fon_code = next((i for i, h in enumerate(header) if "fonasa" in h and "código" in h), 2)
            # Precios: las columnas típicas son "valor paciente particular/fonasa/isapre"
            idx_part = next((i for i, h in enumerate(header) if "particular" in h), None)
            idx_fon = next((i for i, h in enumerate(header) if "fonasa" in h and "valor" in h), None)
            idx_isa = next((i for i, h in enumerate(header) if "isapre" in h), None)

            for row in rows[1:]:
                if len(row) < 3:
                    continue
                nombre = row[idx_pres] if idx_pres < len(row) else ""
                if not nombre or nombre.lower() == query.lower():
                    continue
                # Algunos resultados pueden no contener la palabra; filtramos
                if query.lower() not in nombre.lower():
                    continue
                results.append({
                    "clinica": self.name,
                    "query_busqueda": query,
                    "nombre_prestacion": nombre,
                    "codigo_interno": row[idx_int] if idx_int is not None and idx_int < len(row) else None,
                    "codigo_fonasa": row[idx_fon_code] if idx_fon_code is not None and idx_fon_code < len(row) else None,
                    "precio_particular_clp": parse_clp(row[idx_part]) if idx_part is not None and idx_part < len(row) else None,
                    "precio_fonasa_clp": parse_clp(row[idx_fon]) if idx_fon is not None and idx_fon < len(row) else None,
                    "precio_isapre_clp": parse_clp(row[idx_isa]) if idx_isa is not None and idx_isa < len(row) else None,
                    "url_origen": URL,
                })
        finally:
            await page.close()
        return results
