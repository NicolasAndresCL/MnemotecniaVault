import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import router
from app.config import get_settings
from app.db import session_scope
from app.importers import runner
from app.models import Card, Deck


def _sources(tmp_path):
    vault = tmp_path / "vault" / "01 Proyectos" / "Demo"
    vault.mkdir(parents=True)
    (vault / "nota.md").write_text(
        "# Demo\n\n- **Idempotencia**: propiedad de una operación que da el mismo resultado al repetirla.\n",
        encoding="utf-8",
    )
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "git.json").write_text(
        json.dumps(
            {
                "category": {"slug": "git", "name": "Git", "icon": "commit", "order": 1, "description": "d"},
                "commands": [
                    {
                        "title": "Ver estado",
                        "command": "git status",
                        "section": "Básico",
                        "topic": "Estado",
                        "description": "Muestra el estado del árbol de trabajo.",
                        "examples": [],
                        "tags": ["git"],
                        "level": "básico",
                        "roadmap": ["DevOps"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    proj = tmp_path / "projects" / "Demo"
    proj.mkdir(parents=True)
    (proj / "aprendizaje.md").write_text(
        "# Aprendizaje\n\n## Git\n\n- **Fetch antes de hablar de commits**: las refs remotas locales pueden estar"
        " desactualizadas si ya se pusheó desde otra máquina.\n",
        encoding="utf-8",
    )
    return tmp_path / "vault", seed, tmp_path / "projects"


@pytest.fixture
def configured(db, tmp_path, monkeypatch):
    vault, seed, projects = _sources(tmp_path)
    monkeypatch.setenv("VAULT_PATH", str(vault))
    monkeypatch.setenv("CMDVAULT_SEED_PATH", str(seed))
    monkeypatch.setenv("PROJECTS_PATH", str(projects))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_runner_importa_las_tres_fuentes_y_es_idempotente(configured):
    assert set(runner.configured_sources()) == {"obsidian", "cmdvault", "proyecto"}
    first = {r.source: r for r in runner.run_import()}
    assert all(r.stats["created"] >= 1 for r in first.values())
    again = {r.source: r for r in runner.run_import("cmdvault")}
    assert list(again) == ["cmdvault"] and again["cmdvault"].stats["unchanged"] == 1
    with session_scope() as s:
        assert {d.source for d in s.query(Deck)} == {"obsidian", "cmdvault", "proyecto"}
        assert s.query(Card).count() >= 3


def test_runner_ruta_inexistente(db, tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path / "no-existe"))
    get_settings.cache_clear()
    (res,) = runner.run_import()
    assert res.error and res.stats == {}
    get_settings.cache_clear()


def _client() -> TestClient:
    api = FastAPI()
    api.include_router(router)
    return TestClient(api)


def test_api_health_stats_e_import(configured):
    c = _client()
    assert c.get("/api/health").json()["status"] == "ok"
    assert c.get("/api/stats").json()["total"] == 0
    assert c.post("/api/import", params={"source": "nada"}).status_code == 422
    body = c.post("/api/import").json()
    assert {b["source"] for b in body} == {"obsidian", "cmdvault", "proyecto"}
    assert c.get("/api/stats").json()["total"] >= 3


def test_api_import_exige_api_key_si_esta_configurada(configured, monkeypatch):
    monkeypatch.setenv("API_KEY", "clave")
    get_settings.cache_clear()
    c = _client()
    assert c.post("/api/import").status_code == 401
    assert c.post("/api/import", headers={"X-API-Key": "clave"}).status_code == 200


def test_api_health_503_si_la_bd_falla(db, monkeypatch):
    import app.api as api_mod

    class Roto:
        def connect(self):
            raise ConnectionError("caída")

    monkeypatch.setattr(api_mod, "get_engine", lambda: Roto())
    c = _client()
    assert c.get("/api/health").status_code == 503
    assert c.get("/api/live").status_code == 200  # vivo aunque la BD no responda


def test_runner_fuente_vacia_no_suspende_nada(configured, tmp_path, monkeypatch):
    runner.run_import("cmdvault")
    vacia = tmp_path / "vacia"
    vacia.mkdir()
    monkeypatch.setenv("CMDVAULT_SEED_PATH", str(vacia))
    get_settings.cache_clear()
    (res,) = runner.run_import("cmdvault")
    assert "vacía" in res.error
    with session_scope() as s:
        assert s.query(Card).filter(Card.suspended.is_(True)).count() == 0
