"""Paquete de scrapers para benchmarking de fármacos oncológicos."""
from .isp_chile import ISPChileScraper
from .santa_maria import SantaMariaScraper
from .indisa import IndisaScraper
from .alemana import AlemanaScraper
from .uandes import UAndesScraper
from .davila import DavilaScraper

CLINIC_SCRAPERS = {
    "santa_maria": SantaMariaScraper,
    "indisa":      IndisaScraper,
    "alemana":     AlemanaScraper,
    "uandes":      UAndesScraper,
    "davila":      DavilaScraper,
}

__all__ = [
    "ISPChileScraper",
    "SantaMariaScraper",
    "IndisaScraper",
    "AlemanaScraper",
    "UAndesScraper",
    "DavilaScraper",
    "CLINIC_SCRAPERS",
]
