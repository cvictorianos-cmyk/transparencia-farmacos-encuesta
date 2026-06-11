# Guía de capturas — precios por clínica

Para cada fármaco, **busca por el principio activo Y por cada nombre comercial / biosimilar**
de la lista. Captura siempre la columna **"Particular"** (valor particular), la **glosa**
(nombre exacto del producto) y el **código interno** si aparece.

Clínicas que faltan o conviene refrescar:
- **Clínica Alemana** — faltan 6 fármacos (solo tengo nivolumab). PRIORIDAD.
  Sitio: https://www.clinicaalemana.cl/aranceles/list/insumos-y-medicamentos
- **Clínica Dávila** — opcional, para capturar biosimilares por marca.
  Sitio: https://www.davila.cl/aranceles (categoría **Fármacos**)

> Tip Alemana: al buscar, entra a la página de detalle de cada producto
> (clinicaalemana.cl/aranceles/{código}); ahí aparece el **Valor paciente particular**.

---

## Términos a buscar por fármaco

| # | Fármaco | Principio activo | Marca original | Biosimilares a buscar |
|---|---------|------------------|----------------|------------------------|
| 1 | Pembrolizumab | `pembrolizumab` | `keytruda` | — (no tiene) |
| 2 | Daratumumab (IV 400 mg y SC 1800 mg) | `daratumumab` | `darzalex` | — (no tiene) |
| 3 | Nivolumab | `nivolumab` | `opdivo` | — (no tiene) |
| 4 | Bevacizumab | `bevacizumab` | `avastin` | `abxeda`, `mvasi`, `zirabev`, `krabeva`, `bemabix`, `vegzelma` |
| 5 | Rituximab | `rituximab` | `mabthera` | `truxima`, `rixathon`, `reditux`, `ritemvia` |
| 6 | Cetuximab | `cetuximab` | `erbitux` | — (no tiene) |
| 7 | Ipilimumab | `ipilimumab` | `yervoy` | — (no tiene) |

---

## Qué necesito de cada resultado

Por cada producto que aparezca con precio:
- **Glosa** (ej: "OPDIVO (NIVOLUMAB) 100 MG/10 ML X VIAL")
- **Código interno** (ej: 500820011)
- **Valor particular** en CLP (ej: $1.922.512)
- Marcar si es **original** (marca innovadora) o **bioequivalente/biosimilar**

Con eso lo agrego al catálogo en minutos y aparece en el comparador y el dashboard.

---

## Presentaciones del catálogo (para que coincidan)

- Pembrolizumab: vial **100 mg/4 mL**
- Daratumumab: **400 mg/20 mL** (IV) y **1800 mg/15 mL** (SC, Faspro)
- Nivolumab: **100 mg/10 mL**
- Bevacizumab: **100 mg/4 mL**
- Rituximab: **500 mg/50 mL**
- Cetuximab: **100 mg/20 mL**
- Ipilimumab: **50 mg/10 mL**

(Si aparecen otras concentraciones, captúralas igual; las agrego como presentación extra.)
