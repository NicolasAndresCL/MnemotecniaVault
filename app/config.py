"""Configuración tipada por entorno (variables de entorno o `.env`)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    # SQLite solo para tests y desarrollo rápido; en Compose/producción, Postgres 18.
    database_url: str = "sqlite:///./mnemo.db"
    storage_secret: str = "dev-solo-local-cambiar"
    default_theme: str = "eren"
    port: int = 8080
    timezone: str = "America/Santiago"  # los «días» de la racha y del cupo de nuevas son locales

    # Fuentes de conocimiento (solo lectura). Vacías = fuente desactivada.
    vault_path: Path | None = None  # vault de Obsidian (C:\dev\learning_center)
    cmdvault_seed_path: Path | None = None  # CmdVault/backend/app/seed/data
    projects_path: Path | None = None  # C:\dev\projects (busca */aprendizaje.md)
    import_on_startup: bool = False
    # Si se define, POST /api/import exige la cabecera X-API-Key (para n8n o cron).
    api_key: str = ""

    # Repaso espaciado (FSRS)
    desired_retention: float = 0.9  # probabilidad de recordar que se busca al vencer una tarjeta
    new_per_day: int = 20  # tarjetas nuevas por día (más = más carga futura)
    max_reviews_per_session: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()
