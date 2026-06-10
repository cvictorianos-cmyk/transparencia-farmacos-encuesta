"""Catalogo precargado de farmacos oncologicos de alto costo.

Este modulo entrega un conjunto curado de 10 casos de farmacos oncologicos
para que el comparador web funcione de inmediato (incluso en Render free, sin
ejecutar scraping en vivo). Los precios son REFERENCIALES, construidos a partir
de rangos publicos de aranceles de clinicas privadas y del valor de mercado de
estos biologicos en Chile. No constituyen una cotizacion formal.

Clinicas consideradas (las mismas 5 del benchmark en vivo):
    Clinica Santa Maria, Clinica Indisa, Clinica Alemana,
    Clinica Universidad de los Andes, Clinica Davila.

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
]

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
        },
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
        },
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
        },
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
        },
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
        },
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
        },
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
        },
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
        },
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
        },
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
            })
        presentaciones.append({
            "marca": c["marca"],
            "titular": c["titular"],
            "registro_isp": c["registro_isp"],
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
            "Precios REFERENCIALES con fines academicos (Proyecto de Titulo MSIIN). "
            "No constituyen una cotizacion formal. Verifique siempre con la clinica."
        ),
    }
