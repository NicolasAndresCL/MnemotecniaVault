"""Orquesta los importadores y persiste sus borradores (upsert que conserva el progreso)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.db import session_scope
from app.importers.base import CardDraft, ImportReport
from app.repository import upsert_drafts

log = logging.getLogger(__name__)

Parser = Callable[[Path], tuple[list[CardDraft], ImportReport]]


@dataclass
class SourceResult:
    source: str
    path: str
    report: ImportReport | None
    stats: dict[str, int]
    seconds: float
    error: str = ""


def _parsers() -> dict[str, tuple[Path | None, Parser]]:
    # Import diferido: los parsers solo se cargan cuando se importa.
    from app.importers.cmdvault import parse_cmdvault
    from app.importers.obsidian import parse_vault
    from app.importers.proyectos import parse_projects

    cfg = get_settings()
    return {
        "obsidian": (cfg.vault_path, parse_vault),
        "cmdvault": (cfg.cmdvault_seed_path, parse_cmdvault),
        "proyecto": (cfg.projects_path, parse_projects),
    }


def configured_sources() -> dict[str, str]:
    return {name: str(path) for name, (path, _) in _parsers().items() if path}


def run_import(only: str | None = None) -> list[SourceResult]:
    results: list[SourceResult] = []
    for name, (path, parser) in _parsers().items():
        if only and name != only:
            continue
        if path is None:
            continue
        t0 = time.perf_counter()
        if not Path(path).exists():
            results.append(SourceResult(name, str(path), None, {}, 0.0, "La ruta no existe (¿falta montarla?)"))
            continue
        drafts, report = parser(Path(path))
        if not drafts:
            # Protección: una fuente vacía (montaje faltante, disco desconectado) marcaría como huérfanas
            # TODAS sus tarjetas y las suspendería. Mejor no tocar nada y avisar.
            secs = round(time.perf_counter() - t0, 2)
            results.append(SourceResult(name, str(path), report, {}, secs, "Fuente vacía: no se modificó nada"))
            continue
        with session_scope() as s:
            stats = upsert_drafts(s, drafts, name)
        secs = round(time.perf_counter() - t0, 2)
        log.info("Importación %s: %s (%s s)", name, stats, secs)
        results.append(SourceResult(name, str(path), report, stats, secs))
    return results
