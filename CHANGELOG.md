# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) · Versionado: [SemVer](https://semver.org/lang/es/).

## [Sin publicar]

## [0.1.0] — 2026-11-02

### Agregado
- Repaso espaciado con **FSRS-6** (`fsrs` 6.3.2): recuerdo activo con respuesta escrita, revelado con
  animación, cuatro calificaciones con el intervalo previsto, atajos de teclado (espacio, 1–4), cupo de
  20 nuevas por día y cola **intercalada** entre mazos.
- Importadores en solo lectura: **vault de Obsidian** (definiciones, tablas, cloze, «Pruébate»,
  resúmenes), **CmdVault** (un mazo por entorno) y **`aprendizaje.md` de cada proyecto** (lecciones por
  tecnología). Upsert que conserva el progreso; las tarjetas que desaparecen de la fuente se suspenden.
- **Ganchos mnemotécnicos** por tarjeta (9 técnicas de la skill `mnemotecnia`) con técnica recomendada
  según el tipo de dato y borrador automático; laboratorio con acrónimo + frase absurda, **sistema mayor**
  fonético en español, primeras letras y chunking.
- **Palacio de la memoria**: estaciones, escenas, tarjetas ancladas y recorrido sin mirar.
- **Gimnasio mental**: span de dígitos, sistema mayor y pares asociados con nivel adaptativo y récords.
- Estadísticas (racha, retención 30 días, carga a 30 días, mapa de calor anual, tarjetas más olvidadas) y
  página «El método».
- Temas Eren (por defecto), Luffy y Dark con la convención de tonos de CmdVault.
- API `/api/live`, `/api/health`, `/api/stats` y `POST /api/import` (con `X-API-Key` opcional).
- Docker multi-stage no-root, Compose con Postgres 18, manifiestos de Kubernetes (Kustomize), CI en
  GitHub Actions (lint → tests SQLite y Postgres → build + smoke), release por tag, Jenkinsfile,
  Dependabot y `scripts/verificar.sh` (clon local del CI sobre un clon limpio).
