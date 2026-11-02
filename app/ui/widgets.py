"""Piezas visuales reutilizables."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from app.errors import DomainError

SOURCE_META = {
    "obsidian": ("Vault de Obsidian", "auto_stories"),
    "cmdvault": ("CmdVault", "terminal"),
    "proyecto": ("Lecciones de proyectos", "construction"),
    "manual": ("Creado a mano", "edit_note"),
}

KIND_LABELS = {
    "definicion": "Definición",
    "cloze": "Hueco (cloze)",
    "tabla": "Tabla",
    "pruebate": "Pruébate",
    "resumen": "Resumen",
    "comando": "Comando",
    "leccion": "Lección",
    "manual": "Manual",
}


def page_title(title: str, subtitle: str = "", icon: str | None = None) -> None:
    with ui.row().classes("items-center gap-3 w-full"):
        if icon:
            ui.icon(icon, color="primary").classes("text-4xl")
        with ui.column().classes("gap-0"):
            ui.label(title).classes("mv-h1")
            if subtitle:
                ui.label(subtitle).classes("mv-muted")


def stat_tile(value: str | int, label: str, icon: str, hint: str = "") -> None:
    with ui.card().classes("mv-card p-4 min-w-[10rem] flex-1"), ui.row().classes("items-center gap-3 no-wrap"):
        ui.icon(icon, color="primary").classes("text-3xl opacity-80")
        with ui.column().classes("gap-0"):
            ui.label(str(value)).classes("mv-stat")
            ui.label(label).classes("text-sm mv-muted")
    if hint:
        ui.tooltip(hint)


def md(text: str) -> ui.markdown:
    return ui.markdown(text or "", extras=["fenced-code-blocks", "tables", "cuddled-lists"]).classes("w-full")


def run_safe(fn: Callable[[], object], ok: str | None = None) -> object | None:
    """Ejecuta una acción de dominio; un `DomainError` se muestra como notificación, no como traza."""
    try:
        result = fn()
    except DomainError as exc:
        ui.notify(exc.message, type="negative")
        return None
    if ok:
        ui.notify(ok, type="positive")
    return result


def empty_state(icon: str, title: str, text: str, action: tuple[str, str] | None = None) -> None:
    with ui.card().classes("mv-card w-full items-center p-8 gap-2"):
        ui.icon(icon, color="primary").classes("text-6xl opacity-80")
        ui.label(title).classes("mv-h2")
        ui.label(text).classes("mv-muted text-center")
        if action:
            ui.button(action[0], on_click=lambda: ui.navigate.to(action[1])).props("unelevated color=primary")
