"""Pantallas: cada ruta renderiza y los flujos principales funcionan (simulación sin navegador)."""

import pytest
from nicegui.testing import User

from app.db import session_scope
from app.importers.base import CardDraft
from app.repository import upsert_drafts

pytest_plugins = ["nicegui.testing.user_plugin"]


def _seed() -> None:
    drafts = [
        CardDraft("obsidian-demo", "Demo", "obsidian", f"k{i}", "definicion", f"¿Pregunta {i}?", f"Respuesta {i}")
        for i in range(3)
    ]
    with session_scope() as s:
        upsert_drafts(s, drafts, "obsidian")


@pytest.mark.parametrize(
    ("path", "text"),
    [
        ("/", "Entrena tu memoria"),
        ("/mazos", "Mazos"),
        ("/tarjetas", "Tarjetas"),
        ("/ganchos", "Laboratorio"),
        ("/palacio", "Palacio de la memoria"),
        ("/gimnasio", "Gimnasio"),
        ("/estadisticas", "Estadísticas"),
        ("/importar", "Importar fuentes"),
        ("/metodo", "Pruébate"),
        ("/repaso", "Repaso"),
    ],
)
async def test_rutas_renderizan(user: User, db, path: str, text: str) -> None:
    _seed()
    await user.open(path)
    await user.should_see(text)


async def test_flujo_de_repaso(user: User, db) -> None:
    _seed()
    await user.open("/repaso")
    await user.should_see("¿Pregunta")
    user.find("Mostrar respuesta").click()
    await user.should_see("Respuesta")
    user.find(marker="rate-3").click()
    await user.should_see("2 / ")


async def test_repaso_vacio(user: User, db) -> None:
    await user.open("/repaso")
    await user.should_see("Nada que repasar ahora")


async def test_crear_palacio(user: User, db) -> None:
    await user.open("/palacio")
    user.find("Nuevo palacio").click()
    user.find("Crear").click()
    await user.should_see("Mi casa")
    await user.should_see("Recorrido sin mirar")
