"""Scraper para Clínica Dávila (Recoleta).

URL: https://www.davila.cl/aranceles
Tecnología: SPA basada en Aurelia. Hay que:
1. Seleccionar la sede (default "Clínica Dávila Recoleta").
2. Click categoría (ej: "Fármacos").
3. Llenar input #inlineFormInputGroupUsername con el query.
4. Click botón "Buscar".
5. La tabla muestra el código y el nombre + valor por tipo de paciente (Particular/Fonasa/Isapre).
"""
from __future__ import annotations
from typing import List

from .base import ScraperBase, parse_clp


URL = "https://www.davila.cl/aranceles"


class DavilaScraper(ScraperBase):
    name = "davila"
    base_url = URL

    async def search(self, query: str) -> List[dict]:
        page = await self.new_page()
        results: list[dict] = []
        try:
            await page.goto(URL, wait_until="networkidle", timeout=self.timeout_ms)
            await page.wait_for_timeout(2_500)

            # Click categoría "Fármacos" (medicamentos suelen estar en Fármacos)
            try:
                await page.get_by_text("Fármacos", exact=False).first.click(timeout=4_000)
                await page.wait_for_timeout(1_500)
            except Exception:
                pass

            # Llenar input
            try:
                await page.fill("#inlineFormInputGroupUsername", query)
            except Exception:
                # Fallback por placeholder
                try:
                    await page.get_by_placeholder("código o nombre").fill(query)
                except Exception:
                    pass

            # Click botón Buscar
            try:
                await page.get_by_role("button", name="Buscar").first.click(timeout=4_000)
            except Exception:
                pass
            await page.wait_for_timeout(6_000)

            rows = await page.evaluate(
                """() => {
                    const tables = Array.from(document.querySelectorAll('table'));
                    if (!tables.length) return [];
                    let best = tables[0]; let bestN = best.rows.length;
                    for (const t of tables) { if (t.rows.length > bestN) { best = t; bestN = t.rows.length; } }
                    return Array.from(best.rows).map(r => Array.from(r.cells).map(c => c.innerText.trim()));
                }"""
            )
            if not rows or len(rows) < 2:
                return []

            header = [c.lower() for c in rows[0]]
            idx_cod = next((i for i, h in enumerate(header) if "código" in h or "codigo" in h), 0)
            idx_nom = next((i for i, h in enumerate(header) if "nombre" in h or "prest" in h or "descrip" in h), 1)
            idx_part = next((i for i, h in enumerate(header) if "particular" in h), None)
            idx_fon = next((i for i, h in enumerate(header) if "fonasa" in h), None)
            idx_isa = next((i for i, h in enumerate(header) if "isapre" in h), None)
            idx_valor = next((i for i, h in enumerate(header) if "valor" in h or "precio" in h or "arancel" in h), None)

            for row in rows[1:]:
                if len(row) < 2:
                    continue
                nombre = row[idx_nom] if idx_nom < len(row) else (row[1] if len(row) > 1 else "")
                if not nombre or query.lower() not in nombre.lower():
                    continue
                results.append({
                    "clinica": self.name,
                    "query_busqueda": query,
                    "nombre_prestacion": nombre,
                    "codigo_interno": row[idx_cod] if idx_cod < len(row) else None,
                    "codigo_fonasa": None,
                    "precio_particular_clp": parse_clp(row[idx_part]) if idx_part is not None and idx_part < len(row) else (parse_clp(row[idx_valor]) if idx_valor is not None and idx_valor < len(row) else None),
                    "precio_fonasa_clp": parse_clp(row[idx_fon]) if idx_fon is not None and idx_fon < len(row) else None,
                    "precio_isapre_clp": parse_clp(row[idx_isa]) if idx_isa is not None and idx_isa < len(row) else None,
                    "url_origen": URL,
                    "notas": "Categoría: Fármacos",
                })
        finally:
            await page.close()
        return results
