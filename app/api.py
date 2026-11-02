"""API mínima bajo /api: salud para Docker/K8s, métricas y disparar importaciones (automatizable con n8n)."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from app import __version__
from app.config import get_settings
from app.db import get_engine, session_scope
from app.importers.runner import run_import
from app.repository import overview

router = APIRouter(prefix="/api", tags=["mnemotecnia"])


@router.get("/live")
def live() -> dict:
    """Vivo: el proceso responde. No toca la BD (si la BD cae, reiniciar la app no la arregla)."""
    return {"status": "ok"}


@router.get("/health")
def health() -> dict:
    """Vivo y listo: responde 503 si la base de datos no contesta."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de BD = no listo
        raise HTTPException(status_code=503, detail=f"BD no disponible: {type(exc).__name__}") from exc
    return {"status": "ok", "version": __version__}


@router.get("/stats")
def stats() -> dict:
    with session_scope() as s:
        data = overview(s)
    data.pop("heatmap", None)
    return data


@router.post("/import")
def trigger_import(source: str | None = None, x_api_key: str = Header(default="")) -> list[dict]:
    expected = get_settings().api_key
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Falta o no coincide X-API-Key")
    if source not in (None, "obsidian", "cmdvault", "proyecto"):
        raise HTTPException(status_code=422, detail="source debe ser obsidian, cmdvault o proyecto")
    return [
        {
            "source": r.source,
            "stats": r.stats,
            "seconds": r.seconds,
            "error": r.error,
            "drafts": r.report.drafts if r.report else 0,
        }
        for r in run_import(source)
    ]
