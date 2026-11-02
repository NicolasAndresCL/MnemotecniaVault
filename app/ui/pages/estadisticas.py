"""Estadísticas: carga futura, calidad de las respuestas, dominio por mazo y lo que más se olvida."""

from __future__ import annotations

from datetime import UTC, datetime

from nicegui import ui

from app import srs
from app.db import session_scope
from app.repository import forecast, hardest_cards, list_decks, local_day, overview, rating_breakdown, training_bests
from app.training import GAMES
from app.ui.pages.inicio import heatmap
from app.ui.pages.tarjetas import card_dialog
from app.ui.widgets import empty_state, page_title, stat_tile

RATING_COLORS = {1: "#c0392b", 2: "#e0a43a", 3: "#7fa36b", 4: "#4f8cff"}


def view() -> None:
    page_title("Estadísticas", "Lo que se mide se mejora: retención, carga y puntos débiles.", "insights")
    with session_scope() as s:
        ov = overview(s)
        fc = forecast(s, days=30)
        ratings = rating_breakdown(s)
        decks = [d for d in list_decks(s) if d["total"]]
        hard = [(c.id, c.front.replace("**", "")[:110], c.deck.name, c.lapses) for c in hardest_cards(s)]
        bests = training_bests(s)
    if not ov["total"]:
        empty_state("insights", "Sin datos aún", "Importa fuentes y haz tu primer repaso.", ("Importar", "/importar"))
        return

    with ui.row().classes("w-full gap-4"):
        stat_tile(ov["reviewed_today"], "respuestas hoy", "today")
        stat_tile(ov["active_days"], "días activos (año)", "calendar_month")
        stat_tile(ov["mastered"], "dominadas", "workspace_premium")
        stat_tile(ov["new"], "nuevas por ver", "fiber_new")

    with ui.row().classes("w-full gap-4 items-stretch"):
        with ui.card().classes("mv-card flex-[2] min-w-[22rem] p-4"):
            ui.label("Repasos que vencen (30 días)").classes("mv-h2")
            ui.echart(
                {
                    "tooltip": {"trigger": "axis"},
                    "grid": {"left": 40, "right": 10, "top": 20, "bottom": 30},
                    "xAxis": {"type": "category", "data": [d[5:] for d, _ in fc]},
                    "yAxis": {"type": "value", "minInterval": 1},
                    "series": [
                        {
                            "type": "bar",
                            "data": [n for _, n in fc],
                            "itemStyle": {"borderRadius": [6, 6, 0, 0], "color": "#d9622b"},
                        }
                    ],
                }
            ).classes("w-full h-64")
        with ui.card().classes("mv-card flex-1 min-w-[18rem] p-4"):
            ui.label("Respuestas (30 días)").classes("mv-h2")
            ui.echart(
                {
                    "tooltip": {"trigger": "item"},
                    "series": [
                        {
                            "type": "pie",
                            "radius": ["45%", "75%"],
                            "itemStyle": {"borderRadius": 8},
                            "label": {"color": "#999"},
                            "data": [
                                {"name": srs.RATINGS[r][0], "value": n, "itemStyle": {"color": RATING_COLORS[r]}}
                                for r, n in ratings.items()
                            ],
                        }
                    ],
                }
            ).classes("w-full h-64")

    with ui.card().classes("mv-card w-full p-4"):
        ui.label("Actividad").classes("mv-h2")
        heatmap(ov["heatmap"], local_day(datetime.now(UTC)))

    with ui.row().classes("w-full gap-4 items-stretch"):
        with ui.card().classes("mv-card flex-1 min-w-[22rem] p-4 gap-2"):
            ui.label("Dominio por mazo").classes("mv-h2")
            for d in sorted(decks, key=lambda x: -x["mastery"])[:14]:
                with ui.row().classes("w-full items-center no-wrap gap-2"):
                    ui.label(d["name"]).classes("w-56 ellipsis text-sm")
                    ui.linear_progress(value=d["mastery"] / 100, show_value=False).props(
                        "rounded color=primary size=10px"
                    ).classes("flex-1")
                    ui.label(f"{d['mastery']} %").classes("w-12 text-right text-sm")
        with ui.card().classes("mv-card flex-1 min-w-[22rem] p-4 gap-2"):
            ui.label("Las que más se te olvidan").classes("mv-h2")
            ui.label("Candidatas a un gancho nuevo. Haz clic para crearlo.").classes("text-sm mv-muted")
            if not hard:
                ui.label("Aún ningún olvido en repaso. ¡Bien!").classes("mv-muted")
            for cid, front, deck, lapses in hard:
                with ui.item(on_click=lambda c=cid: card_dialog(c)).props("clickable").classes("rounded-lg w-full"):
                    with ui.item_section():
                        ui.item_label(front)
                        ui.item_label(deck).props("caption")
                    with ui.item_section().props("side"):
                        ui.badge(f"{lapses} olvidos", color="negative")

    with ui.card().classes("mv-card w-full p-4 gap-2"):
        ui.label("Gimnasio mental: récords").classes("mv-h2")
        with ui.row().classes("w-full gap-4"):
            for key, (name, icon, _) in GAMES.items():
                b = bests.get(key, {"best": 0, "played": 0})
                stat_tile(b["best"], f"{name} · {b['played']} partidas", icon)
