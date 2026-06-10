"""Catalogo de farmacos oncologicos con PRECIOS REALES de clinicas chilenas.

Todos los precios provienen de los buscadores publicos de aranceles de cada
clinica (valor particular, horario habil), extraidos en junio de 2026:

    - Clinica INDISA ............... indisa.cl/aranceles-buscador (GraphQL)
    - Clinica Davila ............... davila.cl/aranceles (categoria Farmacos)
    - Clinica U. de los Andes ...... clinicauandes.cl/aranceles/resultado
    - Hospital Clinico UC CHRISTUS . aranceles.ucchristus.cl/api/public (centroId=1)
    - Clinica San Carlos Apoquindo . aranceles.ucchristus.cl/api/public (centroId=3)

Clinica Santa Maria y Clinica Alemana NO publican el valor particular de estos
farmacos oncologicos en su arancel web (Santa Maria solo expone el honorario de
administracion de quimioterapia; Alemana los lista con valor "-"), por lo que no
se incluyen en la comparacion.

No todas las clinicas ofrecen todas las presentaciones: cada caso incluye solo
las clinicas que publican esa presentacion exacta. Precios con fines academicos
(Proyecto de Titulo MSIIN); no constituyen una cotizacion formal.
"""
from __future__ import annotations

from statistics import mean

# Todas las clinicas del catalogo publican precio REAL.
CLINICAS = [
    "Clinica INDISA",
    "Clinica Davila",
    "Clinica Universidad de los Andes",
    "Hospital Clinico UC CHRISTUS",
    "Clinica San Carlos de Apoquindo",
]

FECHA_DATOS = "2026-06 (arancel particular, horario habil)"

CATALOGO: list[dict] = [
    {
        "principio_activo": "pembrolizumab",
        "indicacion": "Inmunoterapia (melanoma, pulmon, otros tumores PD-L1+)",
        "marca": "Keytruda 100 mg/4 mL",
        "titular": "MSD (Merck Sharp & Dohme)",
        "registro_isp": "B-2456/15",
        "presentacion": "Vial 100 mg/4 mL concentrado para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica INDISA": 6_030_118,
            "Clinica Davila": 4_048_980,
            "Clinica Universidad de los Andes": 4_380_828,
            "Hospital Clinico UC CHRISTUS": 4_063_300,
            "Clinica San Carlos de Apoquindo": 4_469_630,
        },
    },
    {
        "principio_activo": "daratumumab",
        "indicacion": "Mieloma multiple (formulacion intravenosa)",
        "marca": "Darzalex IV 400 mg",
        "titular": "Janssen Cilag (Johnson & Johnson)",
        "registro_isp": "B-2711/17",
        "presentacion": "Vial 400 mg/20 mL concentrado para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica INDISA": 2_431_941,
            "Clinica Universidad de los Andes": 2_796_600,
            "Hospital Clinico UC CHRISTUS": 2_319_665,
            "Clinica San Carlos de Apoquindo": 2_530_511,
        },
    },
    {
        "principio_activo": "daratumumab",
        "indicacion": "Mieloma multiple (formulacion subcutanea)",
        "marca": "Darzalex Faspro SC 1800 mg",
        "titular": "Janssen Cilag (Johnson & Johnson)",
        "registro_isp": "B-3110/20",
        "presentacion": "Vial 1800 mg/15 mL solucion subcutanea",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica Universidad de los Andes": 5_616_940,
            "Hospital Clinico UC CHRISTUS": 5_473_958,
            "Clinica San Carlos de Apoquindo": 6_021_353,
        },
    },
    {
        "principio_activo": "nivolumab",
        "indicacion": "Inmunoterapia (melanoma, pulmon, renal)",
        "marca": "Opdivo 100 mg/10 mL",
        "titular": "Bristol Myers Squibb",
        "registro_isp": "B-2502/16",
        "presentacion": "Vial 100 mg/10 mL concentrado para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica INDISA": 2_654_551,
            "Clinica Davila": 1_916_720,
            "Clinica Universidad de los Andes": 2_460_840,
            "Hospital Clinico UC CHRISTUS": 2_129_885,
            "Clinica San Carlos de Apoquindo": 2_321_652,
        },
    },
    {
        "principio_activo": "bevacizumab",
        "indicacion": "Antiangiogenico (colon, pulmon, renal, glioblastoma)",
        "marca": "Avastin 100 mg/4 mL",
        "titular": "Roche",
        "registro_isp": "B-1820/12",
        "presentacion": "Vial 100 mg/4 mL concentrado para perfusion",
        "bioequivalente": True,
        "precios_clinica": {
            "Clinica INDISA": 1_054_823,
            "Clinica Davila": 541_362,
            "Clinica Universidad de los Andes": 660_180,
            "Hospital Clinico UC CHRISTUS": 586_265,
            "Clinica San Carlos de Apoquindo": 644_891,
        },
        "biosimilar": {
            "glosa": "Bevacizumab biosimilar 100 mg (Abxeda, INDISA)",
            "Clinica INDISA": 433_160,
        },
    },
    {
        "principio_activo": "rituximab",
        "indicacion": "Linfoma no Hodgkin, leucemia linfocitica cronica, artritis",
        "marca": "Mabthera 500 mg",
        "titular": "Roche",
        "registro_isp": "B-1455/09",
        "presentacion": "Vial 500 mg/50 mL concentrado para perfusion",
        "bioequivalente": True,
        "precios_clinica": {
            "Clinica INDISA": 3_139_895,
            "Clinica Davila": 1_301_000,
            "Clinica Universidad de los Andes": 1_926_360,
            "Hospital Clinico UC CHRISTUS": 1_750_563,
            "Clinica San Carlos de Apoquindo": 1_925_619,
        },
        "biosimilar": {
            "glosa": "Rituximab biosimilar 500 mg (Rixathon/Truxima/biosimilar UC)",
            "Clinica INDISA": 1_365_214,
            "Clinica Davila": 728_730,
            "Hospital Clinico UC CHRISTUS": 394_485,
            "Clinica San Carlos de Apoquindo": 433_933,
        },
    },
    {
        "principio_activo": "cetuximab",
        "indicacion": "Cancer colorrectal metastasico y de cabeza y cuello",
        "marca": "Erbitux 100 mg/20 mL",
        "titular": "Merck",
        "registro_isp": "B-1602/10",
        "presentacion": "Vial 100 mg/20 mL solucion para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica INDISA": 425_051,
            "Clinica Davila": 502_244,
            "Clinica Universidad de los Andes": 523_020,
            "Hospital Clinico UC CHRISTUS": 472_356,
            "Clinica San Carlos de Apoquindo": 519_591,
        },
    },
    {
        "principio_activo": "ipilimumab",
        "indicacion": "Inmunoterapia (melanoma avanzado, combinaciones)",
        "marca": "Yervoy 50 mg/10 mL",
        "titular": "Bristol Myers Squibb",
        "registro_isp": "B-2380/15",
        "presentacion": "Vial 50 mg/10 mL concentrado para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica INDISA": 4_758_742,
            "Clinica Universidad de los Andes": 3_917_688,
            "Hospital Clinico UC CHRISTUS": 3_588_387,
            "Clinica San Carlos de Apoquindo": 3_947_225,
        },
    },
    {
        "principio_activo": "idursulfasa",
        "indicacion": "Enfermedad de Hunter (mucopolisacaridosis tipo II)",
        "marca": "Elaprase 2 mg/mL",
        "titular": "Takeda (Shire)",
        "registro_isp": "B-1990/13",
        "presentacion": "Vial 6 mg/3 mL concentrado para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Hospital Clinico UC CHRISTUS": 4_308_856,
            "Clinica San Carlos de Apoquindo": 4_739_741,
        },
    },
    {
        "principio_activo": "timoglobulina",
        "indicacion": "Inmunosupresor (rechazo de trasplante, anemia aplasica)",
        "marca": "Timoglobulina 25 mg",
        "titular": "Sanofi (Genzyme)",
        "registro_isp": "B-1340/08",
        "presentacion": "Vial 25 mg polvo para solucion para perfusion",
        "bioequivalente": False,
        "precios_clinica": {
            "Clinica Davila": 817_528,
            "Hospital Clinico UC CHRISTUS": 492_885,
            "Clinica San Carlos de Apoquindo": 542_172,
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
            "n_clinicas": len(precios),
            "precio_min_clp": min(precios),
            "precio_max_clp": max(precios),
            "ahorro_max_clp": max(precios) - min(precios),
            "ahorro_max_pct": round((max(precios) - min(precios)) / max(precios) * 100, 1),
        })
    return out


def comparar(principio_activo: str, marca: str | None = None) -> dict | None:
    """Comparacion de precios reales de un caso entre las clinicas que lo publican."""
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
                "fuente": "real",
            })
        # biosimilar: normalizar a lista de filas {clinica, precio}
        biosim = None
        if c.get("biosimilar"):
            b = c["biosimilar"]
            filas_b = [
                {"clinica": k, "precio_particular_clp": v}
                for k, v in b.items() if k != "glosa"
            ]
            filas_b.sort(key=lambda f: f["precio_particular_clp"])
            biosim = {"glosa": b.get("glosa"), "precios": filas_b,
                      "precio_min_clp": filas_b[0]["precio_particular_clp"] if filas_b else None}
        presentaciones.append({
            "marca": c["marca"],
            "titular": c["titular"],
            "registro_isp": c["registro_isp"],
            "biosimilar": biosim,
            "presentacion": c["presentacion"],
            "indicacion": c["indicacion"],
            "bioequivalente": c["bioequivalente"],
            "n_clinicas": len(precios),
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
            "Precios REALES del arancel particular publicado por cada clinica (" + FECHA_DATOS +
            "), extraidos de sus buscadores oficiales. Clinica Santa Maria y Clinica Alemana no "
            "publican el valor particular de estos farmacos. Fines academicos (Proyecto de Titulo "
            "MSIIN); no constituye una cotizacion formal."
        ),
    }
