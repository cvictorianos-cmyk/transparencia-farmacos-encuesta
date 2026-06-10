# API de Benchmarking de Fármacos Oncológicos

Proyecto de Título — MSIIN — Carlos Victoriano

API REST construida en **FastAPI** que automatiza el benchmarking de precios de medicamentos oncológicos en clínicas privadas de Chile.

## Flujo

1. El usuario solicita un benchmark por **principio activo** (ej: `bevacizumab`).
2. La API consulta el **Registro Sanitario del ISP** (`registrosanitario.ispch.gob.cl`) y obtiene los productos registrados (nombre comercial + titular + número de registro + equivalencia terapéutica).
3. Para cada nombre comercial encontrado, busca aranceles en **5 clínicas privadas**:
    - Clínica Santa María
    - Clínica Indisa
    - Clínica Alemana
    - Clínica Universidad de los Andes
    - Clínica Dávila
4. Persiste los resultados en SQLite y permite exportar a JSON / CSV / Excel.

## Estructura

```
api_benchmarking_oncologico/
├── app/                  # Aplicación FastAPI
│   ├── main.py           # Punto de entrada
│   ├── api.py            # Endpoints REST
│   ├── models.py         # Modelos Pydantic + esquema SQLite
│   ├── database.py       # Conexión SQLite y migraciones
│   └── config.py         # Configuración
├── scrapers/             # Scrapers Playwright
│   ├── base.py           # Clase base ScraperBase
│   ├── isp_chile.py      # Registro Sanitario ISP
│   ├── santa_maria.py    # Clínica Santa María
│   ├── indisa.py         # Clínica Indisa
│   ├── alemana.py        # Clínica Alemana
│   ├── uandes.py         # Clínica UAndes
│   └── davila.py         # Clínica Dávila
├── data/                 # Base de datos SQLite (generada)
├── exports/              # Exportaciones JSON/CSV/Excel
├── scripts/
│   └── run_benchmark.py  # Ejecuta benchmark end-to-end
├── tests/
└── requirements.txt
```

## Instalación

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Uso

### 1. Vía línea de comandos (script)

```bash
python scripts/run_benchmark.py bevacizumab
```

### 2. Vía API REST

```bash
uvicorn app.main:app --reload
```

Luego abrir `http://localhost:8000/docs` para Swagger UI.

#### Endpoints principales

| Método | Ruta                                      | Descripción                                        |
|--------|-------------------------------------------|----------------------------------------------------|
| POST   | `/benchmark/{principio_activo}`           | Ejecuta benchmark completo                         |
| GET    | `/bioequivalentes/{principio_activo}`     | Lista productos del ISP para un principio activo   |
| GET    | `/resultados/{benchmark_id}`              | Resultados de un benchmark                         |
| GET    | `/resultados/{benchmark_id}/export.{fmt}` | Exporta a json / csv / xlsx                        |
| GET    | `/encuesta`                               | Formulario de la encuesta (destino del QR del AFE) |
| POST   | `/encuesta`                               | Guarda una respuesta del censo                     |
| GET    | `/encuestas`                              | Lista las respuestas (censo)                       |
| GET    | `/encuestas/export.csv`                   | Exporta el censo a CSV                             |
| GET    | `/comparador`                             | Comparador web responsivo (móvil y escritorio)     |
| GET    | `/catalogo`                               | Lista los 10 casos oncológicos precargados         |
| GET    | `/comparar/{principio_activo}`            | Compara precios del fármaco entre las 5 clínicas   |
| GET    | `/health`                                 | Healthcheck                                        |

## Comparador web (10 casos precargados)

`/comparador` es una página responsiva (usable desde **celular o computador**, sin
instalar nada) que compara el precio particular de cada fármaco oncológico entre las
cinco clínicas y resalta la más barata y el ahorro potencial, en la línea de GoodRx.

Los datos vienen de `app/catalogo.py`, con **precios REALES** del arancel particular
publicado por cada clínica (jun-2026), extraídos de sus buscadores oficiales:

| Clínica | Fuente | Método |
|---|---|---|
| INDISA | `ng-backend.indisa.cl/wp` | GraphQL (`landingAranceles`) |
| Dávila | `davila.cl/aranceles` (Fármacos) | Buscador JS |
| U. de los Andes | `clinicauandes.cl/aranceles/resultado` | Tabla HTML por `searchQuery` |
| Hospital Clínico UC | `aranceles.ucchristus.cl/api/public` | API pública (centroId=1) |
| San Carlos de Apoquindo | `aranceles.ucchristus.cl/api/public` | API pública (centroId=3) |

Clínica Santa María y Clínica Alemana **no publican** el valor particular de estos
oncológicos (Santa María solo expone el honorario de administración de quimioterapia;
Alemana los lista con valor "-"), por lo que se excluyen. No todas las clínicas
ofrecen todas las presentaciones: cada caso incluye solo las que publican esa
presentación exacta. El comparador no requiere scraping en vivo (datos precargados),
así que corre en el plan **free de Render**.

Los endpoints `/catalogo` y `/comparar/{principio_activo}` exponen los mismos datos
en JSON para integraciones o para el AFE.

## Encuesta / censo (QR del AFE)

El QR del documento AFE apunta a `/encuesta`, un formulario móvil (cuatro bloques:
perfil, experiencia de precios, dolor/disposición y contacto opcional) que guarda
cada respuesta en la tabla `encuestas` de SQLite. Las respuestas se consultan en
`/encuestas` y se descargan con `/encuestas/export.csv`.

### Publicar para que el QR funcione desde celulares

Un QR a `localhost` no funciona desde un teléfono: la API debe estar en una URL pública.

```bash
# Local (pruebas)
uvicorn app.main:app --reload      # http://localhost:8000/encuesta

# Producción (Render): ver render.yaml → https://<servicio>.onrender.com/encuesta
```

Tras desplegar, abre `tools/generar_qr.html`, pega la URL pública (terminada en
`/encuesta`) y descarga el PNG para insertarlo en el AFE.

## Notas técnicas

- El sitio del ISP es ASP.NET WebForms con ViewState dinámico → requiere automatización con navegador.
- Las 5 clínicas tienen estructuras heterogéneas (algunas son SPAs, otras forms tradicionales) → un scraper dedicado por sitio.
- Cada scraper implementa `search(query: str) -> list[Arancel]`.
- Los resultados se normalizan en una tabla unificada con: `clinica`, `nombre_arancel`, `precio_clp`, `unidad`, `url_origen`, `fecha_consulta`.
