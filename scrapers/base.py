"""Clase base para los scrapers de clínicas."""
from __future__ import annotations
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)


def parse_clp(value: str | None) -> Optional[int]:
    """Convierte '$1.234.567' o '1.234.567' a 1234567 (int).
    Retorna None si no parsea."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s in {"-", "—", "N/A", "n/a", ""}:
        return None
    # Quitar símbolo, espacios y separadores de miles
    s = s.replace("$", "").replace("CLP", "").replace("\xa0", "").strip()
    s = s.replace(".", "")
    # Algunos sitios usan "," como decimal; los precios CLP no llevan decimales en esta industria
    s = s.replace(",", "")
    if not re.fullmatch(r"-?\d+", s):
        return None
    return int(s)


class ScraperBase(ABC):
    """Clase base async-context-manager para scrapers de clínicas."""

    name: str = "base"
    base_url: str = ""
    timeout_ms: int = 60_000

    def __init__(self, headless: bool = True, slow_mo: int = 0):
        self.headless = headless
        self.slow_mo = slow_mo
        self._pw = None
        self._browser: Browser | None = None
        self._ctx: BrowserContext | None = None

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless, slow_mo=self.slow_mo
        )
        self._ctx = await self._browser.new_context(
            locale="es-CL", user_agent=USER_AGENT, viewport={"width": 1366, "height": 900}
        )
        return self

    async def __aexit__(self, *exc):
        try:
            if self._ctx:
                await self._ctx.close()
            if self._browser:
                await self._browser.close()
        finally:
            if self._pw:
                await self._pw.stop()

    async def new_page(self):
        assert self._ctx, "Scraper no inicializado (usar 'async with')"
        return await self._ctx.new_page()

    @abstractmethod
    async def search(self, query: str) -> List[dict]:
        """Busca un término y retorna lista de aranceles encontrados (dicts).

        Cada dict debe tener al menos las llaves:
        - clinica (str)
        - query_busqueda (str)
        - nombre_prestacion (str)
        - precio_particular_clp (int|None)
        - codigo_interno, codigo_fonasa, precio_isapre_clp, precio_fonasa_clp, url_origen (opcionales)
        """
        ...
