"""Mazos: uno por fuente/proyecto, con su dominio y lo que vence."""

from __future__ import annotations

from nicegui import ui

from app.db import session_scope
from app.repository import create_deck, list_decks
from app.ui.widgets import SOURCE_META, empty_state, page_title, run_safe


def view() -> None:
    page_title("Mazos", "Cada fuente de conocimiento es un mazo. El anillo es el % de tarjetas dominadas.", "style")

    with ui.row().classes("w-full items-center gap-3"):
        name = ui.input("Nuevo mazo manual (p. ej. «Prueba 2 · Diseño de Software»)").props("outlined dense")
        name.classes("min-w-[24rem]")

        def _create() -> None:
            def _do() -> object:
                with session_scope() as s:
                    return create_deck(s, name.value or "")

            if run_safe(_do, ok="Mazo creado"):
                name.value = ""
                grid.refresh()

        ui.button("Crear", icon="add", on_click=_create).props("unelevated color=primary no-caps")
        ui.space()
        source = ui.toggle(
            {"": "Todos", **{k: v[0].split(" ")[0] for k, v in SOURCE_META.items()}},
            value="",
            on_change=lambda: grid.refresh(),
        ).props("rounded unelevated toggle-color=primary no-caps")

    @ui.refreshable
    def grid() -> None:
        with session_scope() as s:
            decks = [d for d in list_decks(s) if not source.value or d["source"] == source.value]
        if not decks:
            empty_state("inventory_2", "Sin mazos", "Importa tus fuentes o crea uno manual.", ("Importar", "/importar"))
            return
        with ui.element("div").classes("w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"):
            for d in decks:
                _deck_card(d)

    grid()


def _deck_card(d: dict) -> None:
    label, icon = SOURCE_META.get(d["source"], ("", "style"))
    with ui.card().classes("mv-card p-4 gap-3"):
        with ui.row().classes("w-full items-center no-wrap gap-3"):
            ui.circular_progress(d["mastery"], max=100, size="56px", color="primary").props("track-color=grey-8")
            with ui.column().classes("gap-0 flex-1 min-w-0"):
                ui.label(d["name"]).classes("font-bold text-lg ellipsis w-full")
                with ui.row().classes("items-center gap-1"):
                    ui.icon(icon).classes("text-sm opacity-60")
                    ui.label(label).classes("text-xs mv-muted")
        with ui.row().classes("gap-2"):
            ui.badge(f"{d['due']} vencidas", color="primary")
            ui.badge(f"{d['new']} nuevas", color="info").props("outline")
            ui.badge(f"{d['mastered']} dominadas", color="positive").props("outline")
            ui.badge(f"{d['total']} total").props("outline color=grey")
        with ui.row().classes("w-full gap-2"):
            ui.button("Repasar", icon="bolt", on_click=lambda i=d["id"]: ui.navigate.to(f"/repaso?deck={i}")).props(
                "unelevated color=primary no-caps dense"
            )
            ui.button("Tarjetas", icon="list", on_click=lambda i=d["id"]: ui.navigate.to(f"/tarjetas?deck={i}")).props(
                "flat color=primary no-caps dense"
            )
