"""Ganchos: tus anclas mnemotécnicas y el laboratorio para fabricarlas."""

from __future__ import annotations

from nicegui import ui

from app.db import session_scope
from app.mnemonics import (
    MAJOR_TABLE,
    acronym_phrase,
    chunk_digits,
    first_letters,
    initials,
    peg_words,
    word_to_digits,
)
from app.models import TECHNIQUES
from app.repository import list_hooks
from app.ui.pages.tarjetas import card_dialog
from app.ui.widgets import empty_state, md, page_title


def _lab_acronym() -> None:
    with ui.card().classes("mv-card flex-1 min-w-[20rem] p-5 gap-3"):
        ui.label("Acrónimo + frase absurda").classes("mv-h2")
        ui.label("Una lista cerrada que te piden completa → iniciales → frase que se ve.").classes("text-sm mv-muted")
        items = ui.textarea(
            "Un elemento por línea", value="Abstracción\nEncapsulamiento\nModularidad\nJerarquía"
        ).props("outlined autogrow")
        items.classes("w-full")
        out = ui.column().classes("w-full gap-1")
        seed = {"n": 0}

        def run() -> None:
            seed["n"] += 1
            lines = [x for x in (items.value or "").splitlines() if x.strip()]
            out.clear()
            with out:
                ui.label(initials(lines) or "—").classes("mv-digits")
                ui.label(acronym_phrase(lines, seed["n"]) if lines else "").classes("text-lg italic mv-pop")
                ui.label("Cambia la frase por una tuya: la que inventas tú se recuerda mejor.").classes(
                    "text-xs mv-muted"
                )

        ui.button("Generar otra frase", icon="casino", on_click=run).props("outline color=primary no-caps")
        run()


def _lab_major() -> None:
    with ui.card().classes("mv-card flex-1 min-w-[20rem] p-5 gap-3"):
        ui.label("Sistema mayor").classes("mv-h2")
        ui.label(
            "Puertos, versiones, fechas: cada cifra es un sonido; rellena con vocales y sale una palabra."
        ).classes("text-sm mv-muted")
        num = ui.input("Número", value="5432").props("outlined dense")
        pegs = ui.column().classes("w-full gap-1")
        word = ui.input("Palabra → número", value="lámpara").props("outlined dense")
        decoded = ui.label().classes("mv-digits")

        def run_num() -> None:
            pegs.clear()
            with pegs:
                for chunk, words in peg_words(num.value or "").items():
                    with ui.row().classes("items-center gap-2"):
                        ui.label(chunk).classes("mv-chip-tech")
                        ui.label(", ".join(words[:6]) or "sin palabra en el léxico: invéntala").classes("text-sm")

        def run_word() -> None:
            decoded.text = word_to_digits(word.value or "") or "—"

        num.on_value_change(run_num)
        word.on_value_change(run_word)
        run_num()
        run_word()
        with ui.expansion("Tabla del código", icon="table_chart").classes("w-full"):
            ui.table(
                columns=[
                    {"name": "d", "label": "Cifra", "field": "d"},
                    {"name": "s", "label": "Sonidos", "field": "s", "align": "left"},
                    {"name": "t", "label": "Truco", "field": "t", "align": "left"},
                ],
                rows=[{"d": d, "s": s, "t": t} for d, s, t in MAJOR_TABLE],
                row_key="d",
            ).props("flat dense").classes("w-full")


def _lab_text() -> None:
    with ui.card().classes("mv-card flex-1 min-w-[20rem] p-5 gap-3"):
        ui.label("Primeras letras y chunking").classes("mv-h2")
        ui.label("Texto literal (definición exacta, frase de un estándar): deja solo las iniciales.").classes(
            "text-sm mv-muted"
        )
        text = (
            ui.textarea("Texto", value="Revisar y actuar, bajo el mismo candado.")
            .props("outlined autogrow")
            .classes("w-full")
        )
        letters = ui.label().classes("text-xl font-mono")
        digits = ui.input("Tira de cifras (teléfono, RUT, IP)", value="192168001010").props("outlined dense")
        chunks = ui.label().classes("mv-digits")
        text.on_value_change(lambda: letters.set_text(first_letters(text.value or "")))
        digits.on_value_change(lambda: chunks.set_text(chunk_digits(digits.value or "")))
        letters.set_text(first_letters(text.value))
        chunks.set_text(chunk_digits(digits.value))


def view() -> None:
    page_title(
        "Ganchos",
        "El gancho es el «asa» de donde tirar en la prueba. Pocos y fuertes, no muchos y flojos.",
        "anchor",
    )
    with ui.tabs().classes("w-full") as tabs:
        mine = ui.tab("Mis ganchos", icon="anchor")
        lab = ui.tab("Laboratorio", icon="science")
        cat = ui.tab("Qué técnica para qué dato", icon="menu_book")
    with ui.tab_panels(tabs, value=mine).classes("w-full bg-transparent"):
        with ui.tab_panel(mine).classes("gap-3"):
            with session_scope() as s:
                hooks = [(h.card_id, h.technique, h.text, h.card.front, h.card.deck.name) for h in list_hooks(s)]
            if not hooks:
                empty_state(
                    "anchor",
                    "Sin ganchos todavía",
                    "Abre una tarjeta en Tarjetas (o una que falles en el repaso) y crea su gancho.",
                    ("Ir a Tarjetas", "/tarjetas"),
                )
            with ui.element("div").classes("w-full grid grid-cols-1 md:grid-cols-2 gap-4"):
                for card_id, tech, text, front, deck in hooks:
                    with ui.card().classes("mv-card mv-link p-4 gap-2").on("click", lambda c=card_id: card_dialog(c)):
                        with ui.row().classes("items-center gap-2"):
                            ui.label(TECHNIQUES[tech][0]).classes("mv-chip-tech")
                            ui.label(deck).classes("text-xs mv-muted")
                        with ui.element("div").classes("mv-hook w-full"):
                            md(text)
                        ui.label(front.replace("**", "")[:120]).classes("text-sm mv-muted")
        with ui.tab_panel(lab), ui.row().classes("w-full gap-4 items-stretch"):
            _lab_acronym()
            _lab_major()
            _lab_text()
        with ui.tab_panel(cat):
            ui.table(
                columns=[
                    {"name": "t", "label": "Técnica", "field": "t", "align": "left"},
                    {"name": "d", "label": "Tipo de dato", "field": "d", "align": "left"},
                ],
                rows=[{"t": name, "d": data} for name, data in TECHNIQUES.values()],
                row_key="t",
            ).props("flat").classes("w-full mv-card")
            md(
                "**Reglas de calidad** (skill `mnemotecnia`): el gancho lleva al **término exacto**; cada gancho "
                "trae su *Pruébate*; concreto, visual y algo absurdo gana a lo abstracto; no mnemotecnizar lo que "
                "se entiende razonando; si dos ganchos se parecen, se interfieren: cambia uno."
            )
