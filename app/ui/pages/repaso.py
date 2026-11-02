"""Sesión de repaso: recuerdo activo + repaso espaciado FSRS + práctica intercalada."""
# Sin `from __future__ import annotations`: ui.sub_pages inyecta PageArguments mirando la anotación real.

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from nicegui import PageArguments, ui
from nicegui.events import KeyEventArguments

from app import srs
from app.config import get_settings
from app.db import session_scope
from app.mnemonics import answer_similarity
from app.models import TECHNIQUES, Card
from app.repository import get_card, list_decks, record_review, review_queue
from app.ui.widgets import KIND_LABELS, empty_state, md, run_safe


@dataclass
class Session:
    queue: list[int] = field(default_factory=list)
    index: int = 0
    revealed: bool = False
    hint_used: bool = False
    started: float = 0.0
    shown_at: float = 0.0
    done: dict[int, int] = field(default_factory=dict)  # rating → cuántas
    deck_ids: list[int] = field(default_factory=list)
    reveal_fn: Callable[[], None] | None = None
    rate_fn: Callable[[int], None] | None = None


def view(args: PageArguments) -> None:
    deck_param = args.query_parameters.get("deck")
    with session_scope() as s:
        decks = list_decks(s)
    options = {d["id"]: f"{d['name']}  ·  {d['due']} venc. / {d['new']} nuevas" for d in decks if d["total"]}
    st = Session(deck_ids=[int(deck_param)] if deck_param and deck_param.isdigit() else [])

    with ui.row().classes("w-full items-end gap-4"):
        with ui.column().classes("gap-0"):
            ui.label("Repaso").classes("mv-h1")
            ui.label("Intenta recordar ANTES de mirar: el esfuerzo de recuperar es lo que consolida.").classes(
                "mv-muted"
            )
        ui.space()
        deck_select = (
            ui.select(options, multiple=True, value=st.deck_ids, label="Mazos (vacío = todos, intercalados)")
            .props("outlined dense use-chips clearable")
            .classes("min-w-[22rem]")
        )
        ui.button("Nueva sesión", icon="restart_alt", on_click=lambda: start()).props("outline color=primary no-caps")

    progress = ui.linear_progress(value=0, show_value=False).props("rounded color=primary size=10px")
    stage = ui.column().classes("w-full gap-4")

    def start() -> None:
        st.deck_ids = list(deck_select.value or [])
        with session_scope() as s:
            st.queue = [c.id for c in review_queue(s, deck_ids=st.deck_ids or None)]
        st.index, st.done, st.started = 0, {}, time.monotonic()
        render()

    def current() -> Card | None:
        if st.index >= len(st.queue):
            return None
        with session_scope() as s:
            return get_card(s, st.queue[st.index])

    def rate(rating: int, typed: str) -> None:
        if not st.revealed or st.index >= len(st.queue):
            return
        # Usar la pista no impide «Bien», pero sí «Fácil»: si hizo falta ayuda, no fue fácil.
        if st.hint_used and rating == 4:
            rating = 3
        elapsed = int((time.monotonic() - st.shown_at) * 1000)
        cid = st.queue[st.index]

        def _do() -> Card:
            with session_scope() as s:
                return record_review(s, cid, rating, duration_ms=elapsed, typed_answer=typed or None)

        card = run_safe(_do)
        if card is None:
            return
        st.done[rating] = st.done.get(rating, 0) + 1
        # Si sigue en pasos de aprendizaje y vence pronto, vuelve al final de la cola de esta sesión.
        if card.state in (1, 3) and (card.due - datetime.now(UTC)).total_seconds() < 20 * 60:
            st.queue.append(cid)
        st.index += 1
        render()

    def render() -> None:
        stage.clear()
        total = len(st.queue)
        progress.value = st.index / total if total else 0
        card = current()
        st.revealed, st.hint_used = False, False
        with stage:
            if not total:
                empty_state(
                    "celebration",
                    "Nada que repasar ahora",
                    "Vuelve cuando venzan tus tarjetas, sube el cupo de nuevas o importa más fuentes.",
                    ("Ir al gimnasio mental", "/gimnasio"),
                )
                return
            if card is None:
                summary()
                return
            study(card)

    def study(card: Card) -> None:
        st.shown_at = time.monotonic()
        prev = srs.preview(card, desired_retention=get_settings().desired_retention)
        r = srs.retrievability(card)
        with ui.card().classes("mv-card mv-study w-full p-6 gap-4 mv-pop"):
            with ui.row().classes("w-full items-center gap-2"):
                ui.label(card.deck.name).classes("mv-chip-tech")
                ui.badge(KIND_LABELS.get(card.kind, card.kind)).props("outline color=primary")
                ui.badge(srs.STATE_LABELS[card.state]).props("color=info outline")
                if r is not None:
                    ui.label(f"Prob. de recordar: {round(r * 100)} %").classes("text-xs mv-muted")
                ui.space()
                ui.label(f"{st.index + 1} / {len(st.queue)}").classes("text-sm mv-muted")
            with ui.element("div").classes("mv-front w-full"):
                md(card.front)
            answer = (
                ui.textarea(placeholder="Escribe lo que recuerdes (opcional, pero recuerda más quien lo escribe)")
                .props("outlined autogrow dense")
                .classes("w-full")
            )
            hint_box = ui.column().classes("w-full gap-2")
            back_box = ui.column().classes("w-full gap-3")
            with ui.row().classes("w-full items-center gap-2") as controls:
                reveal_btn = ui.button("Mostrar respuesta", icon="visibility", on_click=lambda: reveal()).props(
                    "unelevated color=primary no-caps"
                )
                ui.html('<span class="mv-kbd">Espacio</span>')
                if card.hooks:
                    ui.button("Pista: ver gancho", icon="anchor", on_click=lambda: hint()).props(
                        "flat color=warning no-caps"
                    )
            rating_row = ui.row().classes("w-full gap-3 justify-center")
            rating_row.set_visibility(False)
            with rating_row:
                for value, (label, color) in srs.RATINGS.items():
                    with (
                        ui.button(on_click=lambda v=value: rate(v, answer.value or ""))
                        .props(f"unelevated color={color} no-caps")
                        .classes("min-w-[8.5rem]")
                        .mark(f"rate-{value}"),
                        ui.column().classes("gap-0 items-center"),
                    ):
                        ui.label(label).classes("font-bold")
                        ui.label(f"{srs.format_interval(prev[value])} · [{value}]").classes("text-xs opacity-80")

        def hint() -> None:
            if st.hint_used:
                return
            st.hint_used = True
            with hint_box:
                for h in card.hooks:
                    with ui.element("div").classes("mv-hook w-full mv-pop"):
                        ui.label(TECHNIQUES[h.technique][0]).classes("mv-chip-tech")
                        md(h.text)

        def reveal() -> None:
            if st.revealed:
                return
            st.revealed = True
            controls.set_visibility(False)
            with back_box:
                ui.separator()
                with ui.element("div").classes("w-full mv-reveal"):
                    md(card.back)
                typed = (answer.value or "").strip()
                if typed:
                    sim = answer_similarity(typed, card.back)
                    color = "positive" if sim >= 0.7 else "warning" if sim >= 0.35 else "negative"
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("compare_arrows", color=color)
                        ui.label(f"Coincidencia de palabras clave: {round(sim * 100)} %").classes("text-sm")
                        ui.label("(orienta; tú decides la nota)").classes("text-xs mv-muted")
                if card.hooks and not st.hint_used:
                    for h in card.hooks:
                        with ui.element("div").classes("mv-hook w-full"):
                            ui.label(TECHNIQUES[h.technique][0]).classes("mv-chip-tech")
                            md(h.text)
                if card.context:
                    ui.label(f"Fuente: {card.context}").classes("text-xs mv-muted")
                if card.lapses >= 2 and not card.hooks:
                    ui.label(
                        f"Se te ha olvidado {card.lapses} veces: es momento de crearle un gancho (Tarjetas › abrir)."
                    ).classes("text-sm text-warning")
            rating_row.set_visibility(True)

        reveal_btn.props("autofocus")
        st.reveal_fn = reveal
        st.rate_fn = lambda v: rate(v, answer.value or "")

    def summary() -> None:
        total = sum(st.done.values())
        mins = round((time.monotonic() - st.started) / 60, 1)
        with ui.card().classes("mv-card w-full p-8 items-center gap-3 mv-pop"):
            ui.icon("emoji_events", color="warning").classes("text-7xl")
            ui.label("¡Sesión terminada!").classes("mv-h1")
            ui.label(f"{total} respuestas en {str(mins).replace('.', ',')} min").classes("text-lg mv-muted")
            with ui.row().classes("gap-3"):
                for value, (label, color) in srs.RATINGS.items():
                    ui.badge(f"{label}: {st.done.get(value, 0)}", color=color).classes("text-base px-3 py-1")
            ui.label(
                "Antes de cerrar: intenta recordar 3 tarjetas de esta sesión sin mirar. "
                "Es el mejor minuto extra de estudio que existe."
            ).classes("mv-muted text-center")

    def on_key(e: KeyEventArguments) -> None:
        if not e.action.keydown or e.action.repeat:
            return
        if e.key.space and not st.revealed and st.reveal_fn:
            st.reveal_fn()
        elif st.revealed and e.key.name in ("1", "2", "3", "4") and st.rate_fn:
            st.rate_fn(int(e.key.name))

    ui.keyboard(on_key=on_key, ignore=["input", "select", "button", "textarea"])
    start()
