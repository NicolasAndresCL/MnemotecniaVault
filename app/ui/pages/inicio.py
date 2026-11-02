"""Inicio: el estado de tu memoria de un vistazo."""

from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta

from nicegui import ui

from app.db import session_scope
from app.models import TECHNIQUES
from app.repository import list_decks, list_hooks, local_day, overview
from app.ui.widgets import empty_state, md, stat_tile

MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def heatmap(data: dict[str, int], today: date) -> None:
    """Calendario de actividad de 12 meses (cada repaso o entrenamiento suma)."""
    start = today - timedelta(days=364)
    top = max(data.values(), default=1)
    ui.echart(
        {
            "tooltip": {"position": "top", "formatter": "{c}"},
            "visualMap": {
                "min": 0,
                "max": max(top, 5),
                "show": False,
                "inRange": {"color": ["rgba(128,128,128,.12)", "#e0a43a", "#d9622b", "#a33a1f"]},
            },
            "calendar": {
                "range": [start.isoformat(), today.isoformat()],
                "cellSize": ["auto", 14],
                "left": 30,
                "right": 10,
                "top": 22,
                "itemStyle": {"borderWidth": 3, "borderColor": "rgba(0,0,0,0)", "color": "rgba(128,128,128,.08)"},
                "splitLine": {"show": False},
                "dayLabel": {"firstDay": 1, "nameMap": ["D", "L", "M", "M", "J", "V", "S"], "color": "#999"},
                "monthLabel": {"nameMap": MONTHS, "color": "#999"},
                "yearLabel": {"show": False},
            },
            "series": [{"type": "heatmap", "coordinateSystem": "calendar", "data": list(data.items())}],
        }
    ).classes("w-full h-44")


def view() -> None:
    with session_scope() as s:
        ov = overview(s)
        decks = list_decks(s)
        hooks = [(h.technique, h.text, h.card.front) for h in list_hooks(s, limit=50)]
    today = local_day(datetime.now(UTC))
    pending = ov["due"] + ov["new_left_today"]

    with ui.element("div").classes("mv-hero w-full p-8"), ui.column().classes("gap-3 relative z-10"):
        ui.label("Entrena tu memoria, no tu fuerza de voluntad").classes("mv-h1")
        if pending:
            ui.label(
                f"Hoy te esperan {ov['due']} repasos y {ov['new_left_today']} tarjetas nuevas. "
                "Recuperar justo antes de olvidar es lo que fija el recuerdo."
            ).classes("text-lg mv-muted")
        else:
            ui.label("Estás al día. Aprovecha para crear ganchos o pasar por el gimnasio.").classes("text-lg mv-muted")
        with ui.row().classes("gap-3"):
            ui.button("Empezar repaso", icon="bolt", on_click=lambda: ui.navigate.to("/repaso")).props(
                "unelevated rounded size=lg color=primary no-caps"
            )
            ui.button("Gimnasio mental", icon="fitness_center", on_click=lambda: ui.navigate.to("/gimnasio")).props(
                "outline rounded size=lg color=primary no-caps"
            )

    with ui.row().classes("w-full gap-4"):
        stat_tile(ov["streak"], "días de racha", "local_fire_department", "Días seguidos con actividad")
        stat_tile(ov["due"], "vencidas hoy", "event_repeat")
        stat_tile(ov["mastered"], "dominadas", "workspace_premium", "Estabilidad ≥ 21 días")
        stat_tile(
            f"{ov['retention_30d']} %" if ov["retention_30d"] is not None else "—",
            "retención 30 días",
            "verified",
            "Repasos maduros respondidos sin «Otra vez»",
        )
        stat_tile(ov["total"], "tarjetas activas", "style")

    if not ov["total"]:
        empty_state(
            "cloud_download",
            "Aún no hay tarjetas",
            "Importa tu vault de Obsidian, CmdVault y las lecciones de tus proyectos para empezar.",
            ("Importar fuentes", "/importar"),
        )
        return

    with ui.card().classes("mv-card w-full p-4"):
        ui.label("Actividad del último año").classes("mv-h2")
        heatmap(ov["heatmap"], today)

    with ui.row().classes("w-full gap-4 items-stretch"):
        with ui.card().classes("mv-card flex-1 min-w-[20rem] p-5 gap-2"):
            ui.label("Gancho del día").classes("mv-h2")
            if hooks:
                tech, text, front = random.choice(hooks)
                ui.label(TECHNIQUES[tech][0]).classes("mv-chip-tech")
                with ui.element("div").classes("mv-hook w-full mv-pop"):
                    md(text)
                ui.label("Pruébate: ¿a qué tarjeta pertenece?").classes("text-sm mv-muted")
                with ui.expansion("Ver tarjeta").classes("w-full"):
                    md(front)
            else:
                ui.label(
                    "Todavía no creas ganchos. Cuando una tarjeta se te olvide dos veces, dale un acrónimo, "
                    "una rima o una imagen absurda."
                ).classes("mv-muted")
                ui.button("Ir a Ganchos", on_click=lambda: ui.navigate.to("/ganchos")).props("flat color=primary")
        with ui.card().classes("mv-card flex-1 min-w-[20rem] p-5 gap-2"):
            ui.label("Mazos con más pendientes").classes("mv-h2")
            for d in sorted(decks, key=lambda x: -(x["due"] + min(x["new"], 5)))[:6]:
                with ui.row().classes("w-full items-center no-wrap gap-3"):
                    ui.circular_progress(d["mastery"], max=100, show_value=False, size="34px", color="primary")
                    ui.link(d["name"], f"/repaso?deck={d['id']}").classes("flex-1 no-underline text-inherit")
                    ui.badge(str(d["due"]), color="primary").tooltip("Vencidas")
                    ui.badge(str(d["new"]), color="info").props("outline").tooltip("Nuevas")
