"""Scraper para el Registro Sanitario del ISP de Chile.

Sitio: https://registrosanitario.ispch.gob.cl/
Tecnología: ASP.NET WebForms con ViewState dinámico → requiere navegador.

Búsqueda: marcar checkbox 'Principio Activo' y enviar el término.
La tabla de resultados queda en `#ctl00_ContentPlaceHolder1_gvDatosBusqueda`.
"""
from __future__ import annotations
import re
from typing import List

from playwright.async_api import async_playwright

from .base import USER_AGENT


URL = "https://registrosanitario.ispch.gob.cl/"
SEL_CHK_PRINCIPIO = "#ctl00_ContentPlaceHolder1_chkTipoBusqueda_1"
SEL_TXT_PRINCIPIO = "#ctl00_ContentPlaceHolder1_txtPrincipio"
SEL_BTN_BUSCAR = "#ctl00_ContentPlaceHolder1_btnBuscar"
SEL_GRID = "#ctl00_ContentPlaceHolder1_gvDatosBusqueda"

# Marcas comerciales se extraen del primer token del nombre (suele ser ALL CAPS).
# Ejemplo: "AVASTIN CONCENTRADO PARA SOLUCIÓN PARA INFUSIÓN 100 mg/4 mL (BEVACIZUMAB)"
RE_PRESENT = re.compile(r"(\d+\s?(?:mg|g|UI|U|mL|ml|mcg)[^\s]*\s*/?\s*\d*\s*(?:mg|g|UI|U|mL|ml|mcg)?)", re.I)


def _split_marca_y_presentacion(nombre: str) -> tuple[str, str | None]:
    """Extrae la primera palabra (marca) y la presentación (concentración)."""
    if not nombre:
        return "", None
    primera = nombre.strip().split()[0].upper()
    m = RE_PRESENT.search(nombre)
    presentacion = m.group(1).strip() if m else None
    return primera, presentacion


class ISPChileScraper:
    """Scraper específico para el ISP. No hereda de ScraperBase porque la API
    de salida es distinta (devuelve productos del registro, no aranceles)."""

    name = "isp_chile"

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def buscar_por_principio_activo(self, principio_activo: str) -> List[dict]:
        """Devuelve la lista de productos registrados para un principio activo."""
        productos: List[dict] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            ctx = await browser.new_context(locale="es-CL", user_agent=USER_AGENT)
            page = await ctx.new_page()
            try:
                await page.goto(URL, wait_until="networkidle", timeout=60_000)
                await page.click(SEL_CHK_PRINCIPIO)
                await page.wait_for_selector(SEL_TXT_PRINCIPIO, timeout=15_000)
                await page.fill(SEL_TXT_PRINCIPIO, principio_activo.upper())
                await page.click(SEL_BTN_BUSCAR)
                await page.wait_for_selector(SEL_GRID, timeout=30_000)

                # Extraer todas las filas (incluido header) y omitir header
                rows = await page.evaluate(
                    """
                    (gridSel) => {
                        const t = document.querySelector(gridSel);
                        if (!t) return [];
                        return Array.from(t.rows).map(r =>
                            Array.from(r.cells).map(c => c.innerText.trim())
                        );
                    }
                    """,
                    SEL_GRID,
                )

                if not rows:
                    return []

                # La fila 0 es header, aplica si tiene "Registro" en alguna celda
                header_idx_map = {}
                header = rows[0]
                for i, h in enumerate(header):
                    h_norm = h.lower().strip()
                    if "registro" == h_norm:
                        header_idx_map["registro"] = i
                    elif h_norm == "nombre":
                        header_idx_map["nombre"] = i
                    elif "fecha" in h_norm:
                        header_idx_map["fecha"] = i
                    elif "empresa" in h_norm:
                        header_idx_map["empresa"] = i
                    elif "principio" in h_norm:
                        header_idx_map["principio"] = i
                    elif "control" in h_norm:
                        header_idx_map["control"] = i

                for row in rows[1:]:
                    if len(row) < 5:
                        continue
                    nombre = row[header_idx_map.get("nombre", 2)] if header_idx_map else row[2]
                    marca, presentacion = _split_marca_y_presentacion(nombre)
                    productos.append({
                        "numero_registro": row[header_idx_map.get("registro", 1)] if header_idx_map else row[1],
                        "nombre_comercial": nombre,
                        "nombre_marca": marca,
                        "fecha_registro": row[header_idx_map.get("fecha", 3)] if header_idx_map else row[3],
                        "empresa_titular": row[header_idx_map.get("empresa", 4)] if header_idx_map else row[4],
                        "principio_activo": row[header_idx_map.get("principio", 5)] if header_idx_map else row[5],
                        "control_legal": row[header_idx_map.get("control", 6)] if "control" in header_idx_map else (row[6] if len(row) > 6 else None),
                        "presentacion": presentacion,
                    })
            finally:
                await ctx.close()
                await browser.close()
        return productos

    @staticmethod
    def marcas_unicas(productos: list[dict]) -> list[str]:
        """Devuelve la lista de marcas comerciales únicas (uppercase)."""
        seen = set()
        out: list[str] = []
        for p in productos:
            m = (p.get("nombre_marca") or "").upper().strip()
            if m and m not in seen:
                seen.add(m)
                out.append(m)
        return out
