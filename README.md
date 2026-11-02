# Mnemotecnia Vault — entrenador de memoria con repaso espaciado sobre tu propio conocimiento

[![CI](https://github.com/NicolasAndresCL/MnemotecniaVault/actions/workflows/ci.yml/badge.svg)](https://github.com/NicolasAndresCL/MnemotecniaVault/actions/workflows/ci.yml)
![Versión](https://img.shields.io/badge/versi%C3%B3n-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.14-3776AB)

| | |
|---|---|
| **Versión** | 0.1.0 |
| **Fecha** | 2 de noviembre de 2026 |
| **Autor** | [Nicolás Andrés Cano Leal](#autor) |

Convierte **tu vault de Obsidian, tu biblioteca de comandos CmdVault y las lecciones de cada proyecto**
(`aprendizaje.md`) en tarjetas de estudio, y las programa con **FSRS**, el algoritmo de repaso espaciado
que usa Anki desde 2023. Encima de eso pone las técnicas que mejor funcionan para fijar lo arbitrario:
**ganchos mnemotécnicos** (acrónimos, rimas, imágenes absurdas, contrastes en espejo, sistema mayor),
**palacio de la memoria**, **recuerdo activo** (escribes antes de ver la respuesta), **práctica
intercalada** y un **gimnasio** de memoria de trabajo.

- **UI**: NiceGUI 3.18 (SPA con `ui.sub_pages`), temas Eren · Luffy · Dark.
- **Lógica**: Python 3.14, SQLAlchemy 2.1, `fsrs` 6.3 (FSRS-6).
- **Persistencia**: PostgreSQL 18 (SQLite solo para tests y desarrollo rápido).
- **Todo dockerizado**, con manifiestos de Kubernetes (Kustomize) y pipelines en GitHub Actions y Jenkins.

La **fuente de verdad del contenido son tus notas**: la app las lee en solo lectura. Lo que vive en la base
de datos es tu **progreso** (estado FSRS, repasos, ganchos, palacios y récords del gimnasio).

## Arquitectura

```
app/
  main.py              # entrada: NiceGUI sobre FastAPI, init_db al arrancar, importación inicial opcional
  config.py            # Settings tipados por entorno (pydantic-settings)
  db.py                # engine, session_scope (unidad de trabajo), init_db con pg_advisory_xact_lock
  models.py            # Deck, Card (estado FSRS), Hook, Review, Palace, Locus, TrainingResult + TECHNIQUES
  repository.py        # TODO el SQL: upsert que conserva progreso, cola intercalada, racha, estadísticas
  srs.py               # adaptador FSRS: apply_review, preview de intervalos, recuperabilidad
  mnemonics.py         # técnicas puras: sistema mayor en español, acrónimos, primeras letras, chunking
  training.py          # gimnasio: span de dígitos, sistema mayor, pares asociados (escalera adaptativa)
  errors.py            # DomainError → NotFound / Conflict / InvalidInput
  api.py               # /api/live, /api/health, /api/stats, POST /api/import
  importers/
    base.py            # contrato: CardDraft, ImportReport, make_key (clave estable), filtro de secretos
    markdown.py        # parseo de Markdown: frontmatter, secciones, tablas, negritas, wikilinks
    obsidian.py        # vault → definiciones, tablas, cloze, «Pruébate», resúmenes
    cmdvault.py        # seed JSON de CmdVault → tarjetas de comando
    proyectos.py       # */aprendizaje.md → lecciones por tecnología + cloze
    runner.py          # orquesta las fuentes; una fuente vacía no toca la BD
  ui/
    theme.py           # temas (misma convención de tonos que CmdVault) + CSS con animaciones
    layout.py          # cabecera con racha, menú lateral, rutas
    widgets.py         # piezas reutilizables (stat_tile, md, run_safe…)
    pages/             # inicio, repaso, mazos, tarjetas, ganchos, palacio, gimnasio, estadisticas, importar, metodo
tests/                 # 110 tests: dominio, importadores, API, pantallas (nicegui.testing.User) y versión
k8s/                   # Kustomize: namespace, ConfigMap, StatefulSet de Postgres, Deployment de la app
scripts/verificar.sh   # clon local del CI sobre un clon limpio de HEAD
scripts/smoke.sh       # 14 rutas deben responder 200 en el stack levantado
Dockerfile             # multi-stage, no-root (UID 1000), HEALTHCHECK a /api/health
docker-compose.yml     # db (postgres:18-alpine) → app (:8095→8080), fuentes montadas en solo lectura
Jenkinsfile            # mismo pipeline que el CI, para el Jenkins local
```

**Flujo:** navegador ⇄ (WebSocket) ⇄ `ui/pages` → `repository` → `db` · `importers` → `repository`.
La UI nunca escribe SQL; los importadores nunca tocan la BD (devuelven borradores puros).

## Levantar con Docker

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(24))"   # pegar en POSTGRES_PASSWORD y STORAGE_SECRET
docker compose up -d --build --wait
```

| Servicio | URL |
|---|---|
| App | <http://localhost:8095> |
| Salud (listo, mira la BD) | <http://localhost:8095/api/health> |
| Swagger de la API | <http://localhost:8095/docs> |

Las rutas de tus fuentes se definen en `.env` (`VAULT_HOST_PATH`, `CMDVAULT_HOST_PATH`,
`PROJECTS_HOST_PATH`) y se montan **en solo lectura**. Con `IMPORT_ON_STARTUP=true` la app importa al
arrancar; después se reimporta desde **Importar fuentes** o con `POST /api/import`.

`docker compose down` detiene el stack y **conserva** tu progreso (volumen `pg_data`).
`docker compose down -v` **borra el volumen y con él todo tu progreso**.

## Correr en local sin Docker

Requiere **Python 3.14** (probado con 3.14.3).

```bash
python -m venv env
env/Scripts/pip install -r requirements-dev.txt          # Windows (Linux: env/bin/pip)
export DATABASE_URL=sqlite:///./mnemo.db PORT=8095 \
       VAULT_PATH=C:/dev/learning_center \
       CMDVAULT_SEED_PATH=C:/dev/projects/CmdVault/backend/app/seed/data \
       PROJECTS_PATH=C:/dev/projects IMPORT_ON_STARTUP=true
env/Scripts/python -m app.main
```

## Endpoints

Prefijo `/api`. El resto de las rutas son pantallas de NiceGUI.

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/live` | Vivo: el proceso responde (no toca la BD; para la liveness probe) |
| GET | `/api/health` | Listo: `{"status":"ok","version":…}` o **503** si la BD no contesta |
| GET | `/api/stats` | Totales, vencidas, nuevas del día, dominadas, retención 30 días y racha |
| POST | `/api/import?source=` | Importa `obsidian`, `cmdvault`, `proyecto` o todas; exige `X-API-Key` si `API_KEY` está definida |

```json
{"detail": "source debe ser obsidian, cmdvault o proyecto"}
```

| Código | HTTP | Cuándo |
|---|---|---|
| `InvalidInput` | 422 | `source` desconocido, calificación fuera de 1–4, gancho vacío |
| — | 401 | Falta o no coincide `X-API-Key` |
| `NotFound` | 404 | Tarjeta, mazo, palacio o estación inexistente |
| `Conflict` | 409 | Editar o borrar una tarjeta importada; nombre de mazo o palacio repetido |
| — | 503 | `/api/health` sin base de datos |

## La interfaz

- **Inicio**: racha, vencidas, dominadas, retención, mapa de calor del año y «gancho del día».
- **Repaso**: escribes lo que recuerdas, revelas (barra espaciadora) y calificas con 1–4; cada botón muestra
  el intervalo que dará FSRS. La pista (ver el gancho) impide marcar «Fácil». Las nuevas se sortean entre
  mazos y se limitan a 20 por día.
- **Mazos** y **Tarjetas**: dominio por mazo, búsqueda, tarjetas manuales y el detalle de cada tarjeta con
  su estado FSRS y sus **ganchos** (con técnica recomendada según el tipo de dato y borrador automático).
- **Ganchos**: tus ganchos y un laboratorio (acrónimo + frase absurda, sistema mayor número ⇄ palabra,
  primeras letras, chunking).
- **Palacio de la memoria**: estaciones de un lugar que conoces, una escena por estación, tarjetas ancladas
  y un **recorrido sin mirar**.
- **Gimnasio mental**: span de dígitos, sistema mayor y pares asociados, con récords.
- **Estadísticas**: carga de los próximos 30 días, distribución de respuestas, dominio por mazo y las
  tarjetas que más se olvidan.
- **El método**: por qué funciona cada técnica, con la curva de olvido de FSRS-6 y un «Pruébate» por sección.

Si una fuente no está montada o viene vacía, **Importar** lo informa y no modifica ninguna tarjeta.

## Variables de entorno

| Variable | Por defecto | Para qué |
|---|---|---|
| **`DATABASE_URL`** | `sqlite:///./mnemo.db` | Conexión (en Compose la arma con las de Postgres) |
| **`POSTGRES_PASSWORD`** | — | Contraseña de Postgres (Compose y K8s) |
| **`STORAGE_SECRET`** | `dev-solo-local-cambiar` | Firma del almacenamiento por navegador de NiceGUI |
| `API_KEY` | vacío | Si se define, `POST /api/import` exige `X-API-Key` |
| `VAULT_PATH` · `CMDVAULT_SEED_PATH` · `PROJECTS_PATH` | vacío | Fuentes (vacío = fuente desactivada) |
| `VAULT_HOST_PATH` · `CMDVAULT_HOST_PATH` · `PROJECTS_HOST_PATH` | `./.fuentes-vacias` | Carpetas del host que Compose monta como fuentes |
| `IMPORT_ON_STARTUP` | `false` (`true` en Compose) | Importar al arrancar |
| `NEW_PER_DAY` | `20` | Tarjetas nuevas por día |
| `DESIRED_RETENTION` | `0.9` | Retención objetivo de FSRS (0,70–0,99) |
| `TIMEZONE` | `America/Santiago` | Define el «día» de la racha y del cupo de nuevas |
| `DEFAULT_THEME` | `eren` | `eren`, `luffy` o `dark` |
| `PORT` · `APP_PORT` | `8080` · `8095` | Puerto interno y publicado |

## Kubernetes

```bash
kubectl apply -f k8s/namespace.yaml
kubectl -n mnemotecnia create secret generic mnemotecnia-secrets \
  --from-literal=POSTGRES_PASSWORD=<secreto> --from-literal=STORAGE_SECRET=<secreto>
kubectl apply -k k8s
```

Liveness (`/api/live`) y readiness (`/api/health`) están separadas: si Postgres cae, la app deja de
recibir tráfico pero no entra en un bucle de reinicios. En kind, las fuentes se montan en el nodo con
`extraMounts` en `/fuentes/{vault,cmdvault,proyectos}`, y la imagen se carga con
`kind load docker-image mnemotecnia-vault:0.1.0`.

## Verificación

```bash
./scripts/verificar.sh            # todo el CI sobre un clon limpio de HEAD
./scripts/verificar.sh --sin-docker
```

Reproduce los jobs de `.github/workflows/ci.yml`, en orden:

1. **lint**: `ruff` (versión tomada de `requirements-dev.txt`) `check`, `ruff format --check`, bit de ejecución de los `.sh`, hadolint,
   `docker compose config`, `kubectl kustomize k8s | kubeconform -strict`.
2. **test**: 110 tests con SQLite en memoria (incluye `test_version.py`: la versión coincide en sus 5 lugares), cobertura **≥ 90 %** (actual: 99 %; las vistas se cubren
   con tests de pantalla y el smoke).
3. **test-postgres**: la misma suite contra Postgres 18.
4. **build**: `docker compose up --wait` + `scripts/smoke.sh` (14 rutas) y `down -v` siempre.

## Decisiones de diseño

- **FSRS y no SM-2**: FSRS modela estabilidad, dificultad y recuperabilidad, y agenda cuando la
  probabilidad de recordar cae a la retención pedida. Con el mismo nivel de retención exige menos repasos
  que el SM-2 clásico de Anki. Se usa la librería `fsrs` y no una reimplementación: un error de fórmula aquí
  arruinaría meses de calendario.
- **El progreso sobrevive a la edición de las notas**: la clave de una tarjeta sale de su origen (ruta +
  sección + término), no del texto de la respuesta. Corregir una definición actualiza la tarjeta sin perder
  su historial; borrar la nota la **suspende** en vez de borrarla.
- **Una fuente vacía no toca nada**: si falta un montaje, la importación traería cero tarjetas y, sin esta
  guarda, suspendería todo el progreso de esa fuente.
- **Recuerdo activo antes que reconocimiento**: escribir la respuesta antes de verla es lo que consolida; la
  coincidencia de palabras clave solo orienta y la nota la pones tú.
- **Pocos ganchos y fuertes**: la app recomienda la técnica según el tipo de dato (skill `mnemotecnia`) y
  propone un borrador, pero el gancho lo escribes tú: los ganchos propios se recuerdan mejor.
- **Práctica intercalada por defecto**: la cola mezcla mazos; estudiar en bloques se siente más fácil pero
  rinde menos.
- **Un solo servicio**: NiceGUI ya corre sobre FastAPI, así que la API de salud e importación vive en el
  mismo proceso. Las capas siguen separadas (`repository` concentra el SQL) y una réplica basta: NiceGUI
  guarda el estado de cada pestaña en memoria.
- **Filtro de secretos en profundidad**: el vault ya excluye secretos, pero una nota copiada podría traer
  uno; los importadores descartan contenido con patrones de token o contraseña. El seed de CmdVault es
  público y está exento.

## Autor

**Nicolás Andrés Cano Leal**\
Backend Engineer → SRE | Python · Django · Kubernetes · Terraform · CI/CD

- LinkedIn: [linkedin.com/in/nicolasandrescl](https://www.linkedin.com/in/nicolasandrescl/)
- Portafolio: [nicolasandrescl.github.io](https://nicolasandrescl.github.io/)
- Correo: [nicolas.cano.leal@gmail.com](mailto:nicolas.cano.leal@gmail.com)

Mnemotecnia Vault v0.1.0 · 2 de noviembre de 2026
