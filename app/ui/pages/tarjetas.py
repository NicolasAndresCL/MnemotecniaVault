"""Explorador de tarjetas: buscar, abrir, crear ganchos y tarjetas manuales."""
# Sin `from __future__ import annotations`: ui.sub_pages inyecta PageArguments mirando la anotación real.

from nicegui import PageArguments, ui

from app import srs
from app.db import session_scope
from app.mnemonics import recommend_technique, suggest_hook
from app.models import TECHNIQUES
from app.repository import (
    add_hook,
    create_card,
    delete_hook,
    get_card,
    list_decks,
    search_cards,
    set_suspended,
)
from app.ui.widgets import KIND_LABELS, md, page_title, run_safe

TECH_OPTIONS = {k: v[0] for k, v in TECHNIQUES.items()}


def card_dialog(card_id: int, on_change=None) -> None:  # noqa: ANN001
    """Diálogo de detalle: respuesta, estado FSRS y ganchos (con sugerencia automática)."""
    with ui.dialog().props("maximized=false") as dialog, ui.card().classes("mv-card w-[52rem] max-w-[95vw] p-6 gap-4"):
        body = ui.column().classes("w-full gap-4")

        def render() -> None:
            body.clear()
            with session_scope() as s:
                card = get_card(s, card_id)
                hooks = [(h.id, h.technique, h.text) for h in card.hooks]
                r = srs.retrievability(card)
                deck_name = card.deck.name
            with body:
                with ui.row().classes("w-full items-center gap-2"):
                    ui.label(deck_name).classes("mv-chip-tech")
                    ui.badge(KIND_LABELS.get(card.kind, card.kind)).props("outline color=primary")
                    ui.badge(srs.STATE_LABELS[card.state]).props("outline color=info")
                    if card.suspended:
                        ui.badge("Suspendida", color="negative")
                    ui.space()
                    ui.button(icon="close", on_click=dialog.close).props("flat round dense")
                md(card.front)
                ui.separator()
                md(card.back)
                if card.context:
                    ui.label(f"Fuente: {card.context}").classes("text-xs mv-muted")
                with ui.row().classes("gap-4 text-sm mv-muted"):
                    ui.label(f"Repasos: {card.reps}")
                    ui.label(f"Olvidos: {card.lapses}")
                    if card.stability:
                        ui.label(f"Estabilidad: {card.stability:.1f} d".replace(".", ","))
                    if card.difficulty:
                        ui.label(f"Dificultad: {card.difficulty:.1f}/10".replace(".", ","))
                    if r is not None:
                        ui.label(f"Prob. de recordar hoy: {round(r * 100)} %")

                ui.label("Ganchos").classes("mv-h2")
                for hid, tech, text in hooks:
                    with ui.row().classes("w-full items-start no-wrap gap-2"):
                        with ui.element("div").classes("mv-hook flex-1"):
                            ui.label(TECHNIQUES[tech][0]).classes("mv-chip-tech")
                            md(text)
                        ui.button(icon="delete", on_click=lambda h=hid: _del(h)).props(
                            "flat round dense color=negative"
                        )

                recommended = recommend_technique(card.kind, card.back)
                with ui.row().classes("w-full items-center gap-2"):
                    tech = ui.select(TECH_OPTIONS, value=recommended, label="Técnica").props("outlined dense")
                    tech.classes("min-w-[16rem]")
                    ui.label(f"Recomendada para este dato: {TECHNIQUES[recommended][0]}").classes("text-xs mv-muted")
                hook_text = (
                    ui.textarea(placeholder="Tu gancho: concreto, visual, algo absurdo, y que lleve al término exacto")
                    .props("outlined autogrow")
                    .classes("w-full")
                )
                front, back = card.front, card.back
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Sugerir borrador",
                        icon="auto_awesome",
                        on_click=lambda: hook_text.set_value(suggest_hook(tech.value, front, back)),
                    ).props("outline color=primary no-caps")
                    ui.button(
                        "Guardar gancho", icon="anchor", on_click=lambda: _add(tech.value, hook_text.value)
                    ).props("unelevated color=primary no-caps")
                    ui.space()
                    ui.button(
                        "Reactivar" if card.suspended else "Suspender",
                        icon="play_arrow" if card.suspended else "pause",
                        on_click=lambda: _suspend(not card.suspended),
                    ).props("flat color=grey no-caps")

        def _add(tech: str, text: str) -> None:
            def _do() -> object:
                with session_scope() as s:
                    return add_hook(s, card_id, tech, text or "")

            if run_safe(_do, ok="Gancho guardado: aparecerá como pista en el repaso"):
                render()
                if on_change:
                    on_change()

        def _del(hook_id: int) -> None:
            with session_scope() as s:
                delete_hook(s, hook_id)
            render()

        def _suspend(value: bool) -> None:
            with session_scope() as s:
                set_suspended(s, card_id, value)
            render()
            if on_change:
                on_change()

        render()
    dialog.open()


def view(args: PageArguments) -> None:
    page_title("Tarjetas", "Busca en todo lo importado. Abre una tarjeta para anclarle un gancho.", "search")
    with session_scope() as s:
        decks = {d["id"]: d["name"] for d in list_decks(s)}
    deck_q = args.query_parameters.get("deck")

    with ui.row().classes("w-full items-center gap-3"):
        q = ui.input(placeholder="Buscar en pregunta, respuesta o fuente…").props("outlined dense clearable")
        q.classes("flex-1 min-w-[16rem]")
        deck = ui.select(
            decks, value=int(deck_q) if deck_q and deck_q.isdigit() and int(deck_q) in decks else None, label="Mazo"
        )
        deck.props("outlined dense clearable").classes("min-w-[16rem]")
        kind = ui.select(KIND_LABELS, label="Tipo").props("outlined dense clearable").classes("w-44")
        susp = ui.checkbox("Incluir suspendidas")
        ui.button("Nueva tarjeta", icon="add", on_click=lambda: new_card()).props("unelevated color=primary no-caps")

    @ui.refreshable
    def results() -> None:
        with session_scope() as s:
            cards = search_cards(s, q.value or "", deck.value, kind.value, susp.value, limit=150)
            rows = [
                {
                    "id": c.id,
                    "front": c.front.replace("**", "")[:140],
                    "deck": c.deck.name,
                    "kind": KIND_LABELS.get(c.kind, c.kind),
                    "state": srs.STATE_LABELS[c.state],
                    "hooks": len(c.hooks),
                    "lapses": c.lapses,
                }
                for c in cards
            ]
        ui.label(f"{len(rows)} resultados" + (" (máximo 150: afina la búsqueda)" if len(rows) == 150 else "")).classes(
            "text-sm mv-muted"
        )
        table = ui.table(
            columns=[
                {"name": "front", "label": "Pregunta", "field": "front", "align": "left"},
                {"name": "deck", "label": "Mazo", "field": "deck", "align": "left", "sortable": True},
                {"name": "kind", "label": "Tipo", "field": "kind", "sortable": True},
                {"name": "state", "label": "Estado", "field": "state", "sortable": True},
                {"name": "hooks", "label": "Ganchos", "field": "hooks", "sortable": True},
                {"name": "lapses", "label": "Olvidos", "field": "lapses", "sortable": True},
            ],
            rows=rows,
            row_key="id",
            pagination=20,
        ).classes("w-full mv-card")
        table.props("flat wrap-cells")
        table.on("rowClick", lambda e: card_dialog(e.args[1]["id"], results.refresh))

    for el in (deck, kind, susp):
        el.on_value_change(lambda: results.refresh())
    q.on("keydown.enter", lambda: results.refresh())
    q.on("clear", lambda: results.refresh())
    results()

    def new_card() -> None:
        with ui.dialog() as dlg, ui.card().classes("mv-card w-[40rem] max-w-[95vw] p-6 gap-3"):
            ui.label("Nueva tarjeta").classes("mv-h2")
            d = ui.select(decks, label="Mazo", value=deck.value).props("outlined dense").classes("w-full")
            front = ui.textarea("Pregunta (Markdown)").props("outlined autogrow").classes("w-full")
            back = ui.textarea("Respuesta: el término EXACTO que pide el evaluador").props("outlined autogrow")
            back.classes("w-full")

            def _save() -> None:
                if not d.value:
                    ui.notify("Elige un mazo (crea uno manual en Mazos)", type="warning")
                    return

                def _do() -> object:
                    with session_scope() as s:
                        return create_card(s, d.value, front.value or "", back.value or "")

                if run_safe(_do, ok="Tarjeta creada: entra como nueva en el próximo repaso"):
                    dlg.close()
                    results.refresh()

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                ui.button("Crear", on_click=_save).props("unelevated color=primary no-caps")
        dlg.open()
