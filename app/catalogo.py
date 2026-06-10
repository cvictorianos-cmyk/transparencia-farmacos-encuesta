"""Catalogo precargado de farmacos oncologicos de alto costo.

Este modulo entrega un conjunto curado de 10 casos de farmacos oncologicos
para que el comparador web funcione de inmediato (incluso en Render free, sin
ejecutar scraping en vivo). Los precios son REFERENCIALES, construidos a partir
de rangos publicos de aranceles de clinicas privadas y del valor de mercado de
estos biologicos en Chile. No constituyen una cotizacion formal.

Clinicas consideradas:
    - 5 referenciales del benchmark en vivo: Clinica Santa Maria, Clinica Indisa,
      Clinica Alemana, Clinica Universidad de los Andes, Clinica Davila.
    - 2 con PRECIOS REALES extraidos de la API publica de aranceles de UC CHRISTUS
      (aranceles.ucchristus.cl, /api/public/aranceles/v2, vigencia 2026-04-16,
      valor particular en horario habil): Hospital Clinico UC CHRISTUS y
      Clinica San Carlos de Apoquindo.

Estructura de cada caso:
    principio_activo : nombre INN (minuscula)
    indicacion       : uso clinico principal
    marca            : nombre comercial referencial
    titular          : laboratorio titular del registro ISP
    registro_isp     : numero de registro sanitario referencial
    presentacion     : forma farmaceutica / concentracion
    bioequivalente   : True si existe biosimilar disponible en el mercado
    precios_clinica  : {clinica: precio_particular_clp} por vial/dosis
"""
from __future__ import annotations

from statistics import mean

CLINICAS = [
    "Clinica Santa Maria",
    "Clinica Indisa",
    "Clinica Alemana",
    "Clinica Universidad de los Andes",
    "Clinica Davila",
    "Hospital Clinico UC CHRISTUS",
    "Clinica San Carlos de Apoquindo",
]

# Clinicas cuyos precios provienen de fuente real publica (no referencial)
CLINICAS_FUENTE_REAL = {
    "Hospital Clinico UC CHRISTUS",
    "Clinica San Carlos de Apoquindo",
}

# Nota: precios REFERENCIALES por vial / unidad de dosificacion (CLP, particular).
CATALOGO: list[dict] = [
    {
        "principio_activo": "pembrolizumab",
        "indicacion": "Inmunoterapia (melanoma, pulmon, otros tumores PD-L1+)",
        "marca": "Keytruda",
        "titular": "MSD Chile (Merck Sharp & Dohme)",
        "registro_isp": "B-2456/15",
        "presentacion": "Vial 100 mg/4 mL concentrado para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica Santa Maria": 3_980_000,
            "Clinica Indisa": 3_750_000,
            "Clinica Alemana": 4_250_000,
            "Clinica Universidad de los Andes": 4_090_000,
            "Clinica Davila": 3_690_000,
            "Hospital Clinico UC CHRISTUS": 4_063_300,
            "Clinica San Carlos de Apoquindo": 4_469_630,
        },
        "codigo_uc": "FX0045",
    },
    {
        "principio_activo": "daratumumab",
        "indicacion": "Mieloma multiple (formulacion intravenosa)",
        "marca": "Darzalex IV",
        "titular": "Janssen Cilag (Johnson & Johnson)",
        "registro_isp": "B-2711/17",
        "presentacion": "Vial 400 mg/20 mL concentrado para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica Santa Maria": 3_120_000,
            "Clinica Indisa": 2_980_000,
            "Clinica Alemana": 3_380_000,
            "Clinica Universidad de los Andes": 3_240_000,
            "Clinica Davila": 2_950_000,
            "Hospital Clinico UC CHRISTUS": 2_319_665,
            "Clinica San Carlos de Apoquindo": 2_530_511,
        },
        "codigo_uc": "FO0573",
    },
    {
        "principio_activo": "daratumumab",
        "indicacion": "Mieloma multiple (formulacion subcutanea)",
        "marca": "Darzalex Faspro SC",
        "titular": "Janssen Cilag (Johnson & Johnson)",
        "registro_isp": "B-3110/20",
        "presentacion": "Vial 1800 mg/15 mL solucion subcutanea",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica Santa Maria": 4_480_000,
            "Clinica Indisa": 4_300_000,
            "Clinica Alemana": 4_790_000,
            "Clinica Universidad de los Andes": 4_560_000,
            "Clinica Davila": 4_250_000,
            "Hospital Clinico UC CHRISTUS": 5_473_958,
            "Clinica San Carlos de Apoquindo": 6_021_353,
        },
        "codigo_uc": "FO0641",
    },
    {
        "principio_activo": "nivolumab",
        "indicacion": "Inmunoterapia (melanoma, pulmon, renal)",
        "marca": "Opdivo",
        "titular": "Bristol Myers Squibb",
        "registro_isp": "B-2502/16",
        "presentacion": "Vial 100 mg/10 mL concentrado para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica Santa Maria": 2_350_000,
            "Clinica Indisa": 2_180_000,
            "Clinica Alemana": 2_560_000,
            "Clinica Universidad de los Andes": 2_420_000,
            "Clinica Davila": 2_150_000,
            "Hospital Clinico UC CHRISTUS": 2_129_885,
            "Clinica San Carlos de Apoquindo": 2_321_652,
        },
        "codigo_uc": "FO0152",
    },
    {
        "principio_activo": "bevacizumab",
        "indicacion": "Antiangiogenico (colon, pulmon, renal, glioblastoma)",
        "marca": "Avastin",
        "titular": "Roche Chile",
        "registro_isp": "B-1820/12",
        "presentacion": "Vial 400 mg/16 mL concentrado para perfusion",
        "bioequivalente": True,
        "precios_clinica": {
            "Clinica Santa Maria": 1_290_000,
            "Clinica Indisa": 1_150_000,
            "Clinica Alemana": 1_420_000,
            "Clinica Universidad de los Andes": 1_330_000,
            "Clinica Davila": 1_120_000,
            "Hospital Clinico UC CHRISTUS": 2_024_416,
            "Clinica San Carlos de Apoquindo": 2_226_857,
        },
        "codigo_uc": "FO0516",
    },
    {
        "principio_activo": "rituximab",
        "indicacion": "Linfoma no Hodgkin, leucemia linfocitica cronica, artritis",
        "marca": "Mabthera",
        "titular": "Roche Chile",
        "registro_isp": "B-1455/09",
        "presentacion": "Vial 500 mg/50 mL concentrado para perfusion",
        "bioequivalente": True,
        "precios_clinica": {
            "Clinica Santa Maria": 1_480_000,
            "Clinica Indisa": 1_320_000,
            "Clinica Alemana": 1_590_000,
            "Clinica Universidad de los Andes": 1_510_000,
            "Clinica Davila": 1_290_000,
            "Hospital Clinico UC CHRISTUS": 1_750_563,
            "Clinica San Carlos de Apoquindo": 1_925_619,
        },
        "codigo_uc": "FO0092",
        "biosimilar_uc": {
            "glosa": "Rituximab 500 mg biosimilar (FX9037)",
            "Hospital Clinico UC CHRISTUS": 394_485,
            "Clinica San Carlos de Apoquindo": 433_933,
        },
    },
    {
        "principio_activo": "cetuximab",
        "indicacion": "Cancer colorrectal metastasico y de cabeza y cuello",
        "marca": "Erbitux",
        "titular": "Merck S.A.",
        "registro_isp": "B-1602/10",
        "presentacion": "Vial 100 mg/20 mL solucion para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica Santa Maria": 980_000,
            "Clinica Indisa": 920_000,
            "Clinica Alemana": 1_080_000,
            "Clinica Universidad de los Andes": 1_010_000,
            "Clinica Davila": 895_000,
            "Hospital Clinico UC CHRISTUS": 472_356,
            "Clinica San Carlos de Apoquindo": 519_591,
        },
        "codigo_uc": "FO0123",
    },
    {
        "principio_activo": "ipilimumab",
        "indicacion": "Inmunoterapia (melanoma avanzado, combinaciones)",
        "marca": "Yervoy",
        "titular": "Bristol Myers Squibb",
        "registro_isp": "B-2380/15",
        "presentacion": "Vial 50 mg/10 mL concentrado para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica Santa Maria": 5_120_000,
            "Clinica Indisa": 4_880_000,
            "Clinica Alemana": 5_490_000,
            "Clinica Universidad de los Andes": 5_260_000,
            "Clinica Davila": 4_790_000,
            "Hospital Clinico UC CHRISTUS": 3_588_387,
            "Clinica San Carlos de Apoquindo": 3_947_225,
        },
        "codigo_uc": "FO0160",
    },
    {
        "principio_activo": "idursulfasa",
        "indicacion": "Enfermedad de Hunter (mucopolisacaridosis tipo II)",
        "marca": "Elaprase",
        "titular": "Takeda (Shire)",
        "registro_isp": "B-1990/13",
        "presentacion": "Vial 6 mg/3 mL concentrado para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica Santa Maria": 2_780_000,
            "Clinica Indisa": 2_640_000,
            "Clinica Alemana": 2_990_000,
            "Clinica Universidad de los Andes": 2_850_000,
            "Clinica Davila": 2_590_000,
            "Hospital Clinico UC CHRISTUS": 4_308_856,
            "Clinica San Carlos de Apoquindo": 4_739_741,
        },
        "codigo_uc": "FX0063",
    },
    {
        "principio_activo": "timoglobulina",
        "indicacion": "Inmunosupresor (rechazo de trasplante, anemia aplasica)",
        "marca": "Timoglobulina (anti-timocitica)",
        "titular": "Sanofi (Genzyme)",
        "registro_isp": "B-1340/08",
        "presentacion": "Vial 25 mg polvo para solucion para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica Santa Maria": 520_000,
            "Clinica Indisa": 478_000,
            "Clinica Alemana": 565_000,
            "Clinica Universidad de los Andes": 540_000,
            "Clinica Davila": 462_000,
            "Hospital Clinico UC CHRISTUS": 492_885,
            "Clinica San Carlos de Apoquindo": 542_172,
        },
        "codigo_uc": "FO0007",
    },
]


def _slug(s: str) -> str:
    return s.strip().lower()


def listar_catalogo() -> list[dict]:
    """Devuelve una vista resumida de los casos disponibles."""
    out = []
    for c in CATALOGO:
        precios = list(c["precios_clinica"].values())
        out.append({
            "principio_activo": c["principio_activo"],
            "marca": c["marca"],
            "indicacion": c["indicacion"],
            "presentacion": c["presentacion"],
            "bioequivalente": c["bioequivalente"],
            "precio_min_clp": min(precios),
            "precio_max_clp": max(precios),
            "ahorro_max_clp": max(precios) - min(precios),
            "ahorro_max_pct": round((max(precios) - min(precios)) / max(precios) * 100, 1),
        })
    return out


def comparar(principio_activo: str, marca: str | None = None) -> dict | None:
    """Comparacion de precios de un caso entre las 5 clinicas.

    Si un principio activo tiene varias presentaciones (ej. daratumumab IV/SC),
    devuelve todas, o filtra por `marca` si se entrega.
    """
    pa = _slug(principio_activo)
    casos = [c for c in CATALOGO if _slug(c["principio_activo"]) == pa]
    if marca:
        m = _slug(marca)
        casos = [c for c in casos if m in _slug(c["marca"])]
    if not casos:
        return None

    presentaciones = []
    for c in casos:
        precios = c["precios_clinica"]
        ordenados = sorted(precios.items(), key=lambda kv: kv[1])
        precio_min = ordenados[0][1]
        precio_max = ordenados[-1][1]
        promedio = round(mean(precios.values()))
        filas = []
        for clinica, precio in ordenados:
            filas.append({
                "clinica": clinica,
                "precio_particular_clp": precio,
                "es_menor": precio == precio_min,
                "sobreprecio_vs_min_clp": precio - precio_min,
                "sobreprecio_vs_min_pct": round((precio - precio_min) / precio_min * 100, 1),
                "fuente": "real" if clinica in CLINICAS_FUENTE_REAL else "referencial",
            })
        presentaciones.append({
            "marca": c["marca"],
            "titular": c["titular"],
            "registro_isp": c["registro_isp"],
            "codigo_uc": c.get("codigo_uc"),
            "biosimilar_uc": c.get("biosimilar_uc"),
            "presentacion": c["presentacion"],
            "indicacion": c["indicacion"],
            "bioequivalente": c["bioequivalente"],
            "precio_min_clp": precio_min,
            "precio_max_clp": precio_max,
            "precio_promedio_clp": promedio,
            "ahorro_clp": precio_max - precio_min,
            "ahorro_pct": round((precio_max - precio_min) / precio_max * 100, 1),
            "clinica_mas_barata": ordenados[0][0],
            "clinica_mas_cara": ordenados[-1][0],
            "precios": filas,
        })

    return {
        "principio_activo": pa,
        "n_presentaciones": len(presentaciones),
        "presentaciones": presentaciones,
        "disclaimer": (
            "Fines academicos (Proyecto de Titulo MSIIN). Hospital Clinico UC CHRISTUS y "
            "Clinica San Carlos de Apoquindo: precios REALES del arancel publico "
            "aranceles.ucchristus.cl (valor particular, horario habil, vigencia 2026-04-16). "
            "Resto de clinicas: precios referenciales. No constituye cotizacion formal."
        ),
    }
