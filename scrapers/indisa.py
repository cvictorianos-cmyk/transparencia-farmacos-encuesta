"""Scraper Clinica Indisa via GraphQL backend."""
from __future__ import annotations
import json
from typing import List
from urllib.parse import quote

import httpx

from .base import ScraperBase, parse_clp


URL_PUBLIC = "https://www.indisa.cl/aranceles-buscador?param=medicamentos"
GQL_BASE = "https://ng-backend.indisa.cl/wp/index.php"
PERSISTED_HASH = "bf0f817f735780b095df216d3b3d06545663e99c66ca98a7e58b02577c9d48e2"


def _gql_url(query: str) -> str:
    variables = {
        "param": "medicamentos",
        "araprev": "particular",
        "aracode": "",
        "araname": query,
        "uri": "/aranceles-buscador/",
    }
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": PERSISTED_HASH}}
    return (
        f"{GQL_BASE}?graphql&operationName=GetPageData"
        f"&variables={quote(json.dumps(variables))}"
        f"&extensions={quote(json.dumps(extensions))}"
    )


class IndisaScraper(ScraperBase):
    name = "indisa"
    base_url = URL_PUBLIC

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, */*",
                "Origin": "https://www.indisa.cl",
                "Referer": "https://www.indisa.cl/",
            },
        )
        return self

    async def __aexit__(self, *exc):
        await self._client.aclose()

    async def search(self, query: str) -> List[dict]:
        results: list[dict] = []
        try:
            r = await self._client.get(_gql_url(query))
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            return [{"clinica": self.name, "query_busqueda": query,
                     "nombre_prestacion": "[ERROR]", "notas": f"GraphQL: {e}",
                     "url_origen": URL_PUBLIC}]
        items = (data.get("data") or {}).get("page", {}).get("landingAranceles", []) or []
        for it in items:
            if not isinstance(it, dict):
                continue
            nombre = it.get("service_detail") or ""
            if not nombre:
                continue
            results.append({
                "clinica": self.name,
                "query_busqueda": query,
                "nombre_prestacion": nombre,
                "codigo_interno": it.get("internal_id"),
                "codigo_fonasa": it.get("fonasa_code"),
                "precio_particular_clp": parse_clp(it.get("med_value") or it.get("value")),
                "precio_isapre_clp": None,
                "precio_fonasa_clp": None,
                "url_origen": URL_PUBLIC,
                "notas": f"category={it.get('category')}; sub={it.get('subcategory')}",
            })
        return results
