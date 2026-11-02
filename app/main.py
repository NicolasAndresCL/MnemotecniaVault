"""Punto de entrada: NiceGUI (sobre FastAPI) + API /api + BD inicializada al arrancar."""

from __future__ import annotations

import logging

from nicegui import app, ui

from app import __version__
from app.api import router
from app.config import get_settings
from app.db import init_db
from app.ui.layout import root

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mnemotecnia")

app.include_router(router)


@app.on_startup
async def _startup() -> None:
    init_db()
    if get_settings().import_on_startup:
        from nicegui import run

        from app.importers.runner import run_import

        results = await run.io_bound(run_import)
        log.info("Importación inicial: %s", [(r.source, r.stats, r.error) for r in results])
    log.info("Mnemotecnia Vault %s lista", __version__)


def main() -> None:
    cfg = get_settings()
    ui.run(
        root,
        title="Mnemotecnia Vault",
        favicon="🧠",
        port=cfg.port,
        host="0.0.0.0",  # noqa: S104 — en el contenedor; Compose decide qué se publica
        storage_secret=cfg.storage_secret,
        language="es",
        reload=False,
        show=False,
        dark=None,
        fastapi_docs=True,  # Swagger en /docs para la API de salud e importación
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
