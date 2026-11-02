"""Marco de la SPA: tema, cabecera, menú lateral y rutas (`ui.sub_pages`)."""

from __future__ import annotations

from nicegui import app, ui

from app.config import get_settings
from app.db import session_scope
from app.repository import overview
from app.ui.pages import estadisticas, ganchos, gimnasio, importar, inicio, mazos, metodo, palacio, repaso, tarjetas
from app.ui.theme import BASE_CSS, FONTS, THEMES, css_variables, get_theme

NAV = [
    ("Inicio", "space_dashboard", "/"),
    ("Repasar", "bolt", "/repaso"),
    ("Mazos", "style", "/mazos"),
    ("Tarjetas", "search", "/tarjetas"),
    ("Ganchos", "anchor", "/ganchos"),
    ("Palacio de la memoria", "castle", "/palacio"),
    ("Gimnasio mental", "fitness_center", "/gimnasio"),
    ("Estadísticas", "insights", "/estadisticas"),
    ("Importar fuentes", "sync", "/importar"),
    ("El método", "school", "/metodo"),
]

ROUTES = {
    "/": inicio.view,
    "/repaso": repaso.view,
    "/mazos": mazos.view,
    "/tarjetas": tarjetas.view,
    "/ganchos": ganchos.view,
    "/palacio": palacio.view,
    "/gimnasio": gimnasio.view,
    "/estadisticas": estadisticas.view,
    "/importar": importar.view,
    "/metodo": metodo.view,
}


def current_theme_key() -> str:
    return app.storage.user.get("theme", get_settings().default_theme)


def _set_theme(key: str) -> None:
    app.storage.user["theme"] = key
    ui.navigate.reload()


def root() -> None:
    theme = get_theme(current_theme_key())
    ui.add_head_html(FONTS)
    ui.add_css(BASE_CSS + css_variables(theme))
    ui.colors(**theme.quasar)
    ui.dark_mode(theme.dark)  # un único dark_mode por página

    with session_scope() as s:
        ov = overview(s)

    with ui.header().classes("items-center gap-3 px-4 py-2"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()).props("flat round color=primary")
        with ui.link(target="/").classes("no-underline"), ui.row().classes("items-center gap-2 no-wrap"):
            ui.icon("psychology", color="primary").classes("text-3xl")
            ui.label("Mnemotecnia Vault").classes("mv-brand")
        ui.space()
        with ui.row().classes("items-center gap-1 no-wrap").tooltip("Días seguidos repasando o entrenando"):
            ui.icon("local_fire_department").classes("mv-flame text-2xl")
            ui.label(f"{ov['streak']} d").classes("font-bold")
        with (
            ui.button(on_click=lambda: ui.navigate.to("/repaso"))
            .props("unelevated rounded color=primary no-caps")
            .tooltip("Tarjetas vencidas + nuevas del día")
        ):
            ui.icon("bolt")
            ui.label(f"{ov['due'] + ov['new_left_today']} por repasar").classes("ml-1")
        ui.select(
            {k: t.label for k, t in THEMES.items()},
            value=current_theme_key(),
            on_change=lambda e: _set_theme(e.value),
        ).props("dense outlined options-dense").classes("w-52").tooltip("Tema")

    with ui.left_drawer(value=True).props("width=250 bordered") as drawer, ui.column().classes("w-full gap-0 py-2"):
        for label, icon, href in NAV:
            with ui.item(on_click=lambda h=href: ui.navigate.to(h)).classes("rounded-lg mx-2").props("clickable"):
                with ui.item_section().props("avatar"):
                    ui.icon(icon, color="primary")
                with ui.item_section():
                    ui.item_label(label)
        ui.space()
        ui.label(theme.tagline).classes("text-xs mv-muted px-4 pt-6 italic")

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-5"):
        ui.sub_pages(ROUTES).classes("w-full")
