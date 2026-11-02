"""Gimnasio mental: span de dígitos, sistema mayor y pares asociados (lógica en `app.training`)."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from nicegui import ui

from app import training
from app.db import session_scope
from app.mnemonics import MAJOR_TABLE, chunk_digits, word_to_digits
from app.repository import save_training, training_bests
from app.ui.widgets import page_title, run_safe

DIGIT_ATTEMPTS = 5  # intentos por ronda de dígitos
MAJOR_ROUND = 10  # preguntas por ronda de sistema mayor
SECONDS_PER_DIGIT = 0.8
SECONDS_PER_PAIR = 6.0
TICK = 0.1


def _save(game: str, score: int, level: int, details: dict) -> None:
    def _do() -> None:
        with session_scope() as s:
            save_training(s, game, score, level, details)

    run_safe(_do)


def _best_header(game: str) -> Callable[[], None]:
    """Cabecera con el récord del juego; devuelve la función que la refresca tras guardar."""
    title, icon, hint = training.GAMES[game]
    box = ui.row().classes("w-full items-center gap-3")

    def refresh() -> None:
        with session_scope() as s:
            info = training_bests(s).get(game, {"best": 0, "played": 0})
        box.clear()
        with box:
            ui.icon(icon, color="primary").classes("text-3xl")
            with ui.column().classes("gap-0"):
                ui.label(title).classes("mv-h2")
                ui.label(hint).classes("mv-muted text-sm")
            ui.space()
            ui.badge(f"Récord: {info['best']}", color="warning").classes("text-base px-3 py-1")
            ui.badge(f"Intentos: {info['played']}").props("outline color=primary").classes("text-base px-3 py-1")

    refresh()
    return refresh


def _summary(stage: ui.column, title: str, lines: list[str], again: Callable[[], None]) -> None:
    with stage, ui.card().classes("mv-card w-full p-6 items-center gap-3 mv-pop"):
        ui.icon("emoji_events", color="warning").classes("text-6xl")
        ui.label(title).classes("mv-h2")
        for line in lines:
            ui.label(line).classes("mv-muted")
        ui.button("Otra ronda", icon="replay", on_click=again).props("unelevated color=primary no-caps")


def _countdown_bar() -> ui.linear_progress:
    return ui.linear_progress(value=1, show_value=False).props("rounded color=primary size=10px").classes("w-full")


# --------------------------------------------------------------------------- 1. span de dígitos
@dataclass
class DigitsState:
    level: training.Level = field(default_factory=training.Level)
    attempt: int = 0
    best_in_round: int = 0
    seq: str = ""
    timer: ui.timer | None = None


def _digits_game() -> None:
    st = DigitsState()
    refresh_best = _best_header("digitos")
    with ui.row().classes("w-full items-center gap-4"):
        grouped = ui.switch("Ver agrupado (chunking)", value=True)
        ui.label(
            "Consejo: convierte pares de cifras en palabras con el sistema mayor (47 = roca, 13 = tema) "
            "y memoriza una mini historia en vez de cifras sueltas."
        ).classes("mv-muted text-sm flex-1")
    stage = ui.column().classes("w-full gap-4")

    def stop_timer() -> None:
        if st.timer is not None:
            st.timer.cancel()
            st.timer = None

    def new_round() -> None:
        st.attempt, st.best_in_round = 0, 0
        next_attempt()

    def next_attempt() -> None:
        stop_timer()
        st.seq = training.digit_sequence(st.level.value)
        total = SECONDS_PER_DIGIT * len(st.seq)
        elapsed = [0.0]
        stage.clear()
        with stage, ui.card().classes("mv-card w-full p-6 items-center gap-4"):
            ui.label(
                f"Intento {st.attempt + 1} de {DIGIT_ATTEMPTS} · nivel {st.level.value} · mejor nivel {st.level.best}"
            ).classes("mv-muted")
            shown = chunk_digits(st.seq) if grouped.value else st.seq
            ui.label(shown).classes("mv-digits mv-pop")
            bar = _countdown_bar()
            ui.label(f"Tienes {total:.1f} s para memorizarla".replace(".", ",")).classes("mv-muted text-sm")

            def tick(bar: ui.linear_progress = bar, elapsed: list[float] = elapsed, total: float = total) -> None:
                elapsed[0] += TICK
                bar.value = max(0.0, 1 - elapsed[0] / total)
                if elapsed[0] >= total:
                    stop_timer()
                    recall()

            st.timer = ui.timer(TICK, tick)

    def recall() -> None:
        stage.clear()
        with stage, ui.card().classes("mv-card w-full p-6 items-center gap-4"):
            ui.label("¿Cuál era la tira? Escríbela de memoria y presiona Enter").classes("mv-h2")
            box = ui.input(placeholder="Cifras").props("outlined autofocus").classes("w-80")
            box.on("keydown.enter", lambda: submit(box.value or ""))
            ui.button("Comprobar", icon="check", on_click=lambda: submit(box.value or "")).props(
                "unelevated color=primary no-caps"
            )

    def submit(typed: str) -> None:
        ok = training.check_digits(st.seq, typed)
        length = len(st.seq)
        level_used = st.level.value
        st.level.record(ok)
        st.attempt += 1
        if ok:
            st.best_in_round = max(st.best_in_round, length)
        _save("digitos", length if ok else 0, level_used, {"largo": length, "acierto": ok, "escrito": typed[:60]})
        refresh_best()
        stage.clear()
        with stage, ui.card().classes("mv-card w-full p-6 items-center gap-3 mv-pop"):
            ui.icon("check_circle" if ok else "cancel", color="positive" if ok else "negative").classes("text-6xl")
            ui.label("¡Correcto!" if ok else "No coincide").classes("mv-h2")
            ui.label("Secuencia correcta:").classes("mv-muted")
            ui.label(chunk_digits(st.seq)).classes("mv-digits")
            ui.label(f"Nivel actual: {st.level.value} · mejor nivel: {st.level.best}").classes("mv-muted")
            last = st.attempt >= DIGIT_ATTEMPTS
            ui.button(
                "Ver resumen" if last else "Siguiente",
                icon="flag" if last else "arrow_forward",
                on_click=finish if last else next_attempt,
            ).props("unelevated color=primary no-caps")

    def finish() -> None:
        stop_timer()
        stage.clear()
        aciertos = sum(st.level.history[-DIGIT_ATTEMPTS:])
        _summary(
            stage,
            f"Largo máximo logrado: {st.best_in_round}",
            [f"{aciertos} aciertos de {DIGIT_ATTEMPTS} · el nivel sigue en {st.level.value} para la próxima ronda"],
            new_round,
        )

    new_round()


# --------------------------------------------------------------------------- 2. sistema mayor
@dataclass
class MajorState:
    mode: str = "num_palabra"  # num_palabra | palabra_num
    index: int = 0
    correct: int = 0
    started: float = 0.0
    number: str = ""
    word: str = ""


def _major_game() -> None:
    st = MajorState()
    refresh_best = _best_header("sistema_mayor")
    with ui.expansion("Tabla de referencia del sistema mayor", icon="table_chart").classes("mv-card w-full"):
        ui.table(
            columns=[
                {"name": "d", "label": "Cifra", "field": "d", "align": "center"},
                {"name": "s", "label": "Sonidos", "field": "s", "align": "left"},
                {"name": "t", "label": "Truco", "field": "t", "align": "left"},
            ],
            rows=[{"d": d, "s": s, "t": t} for d, s, t in MAJOR_TABLE],
            row_key="d",
        ).props("flat dense").classes("w-full")
    mode = ui.toggle({"num_palabra": "Número → palabra", "palabra_num": "Palabra → número"}, value=st.mode).props(
        "no-caps color=primary"
    )
    stage = ui.column().classes("w-full gap-4")

    def new_round() -> None:
        st.mode = mode.value
        st.index, st.correct, st.started = 0, 0, time.monotonic()
        ask()

    def ask() -> None:
        st.number, st.word = training.major_challenge()
        stage.clear()
        with stage, ui.card().classes("mv-card w-full p-6 items-center gap-4"):
            ui.label(f"Pregunta {st.index + 1} de {MAJOR_ROUND} · aciertos: {st.correct}").classes("mv-muted")
            if st.mode == "num_palabra":
                ui.label(st.number).classes("mv-digits mv-pop")
                ui.label("Escribe cualquier palabra cuyos sonidos consonantes codifiquen este número").classes(
                    "mv-muted"
                )
                placeholder = "Palabra"
            else:
                ui.label(st.word).classes("mv-h1 mv-pop")
                ui.label("¿Qué número codifica esta palabra?").classes("mv-muted")
                placeholder = "Número"
            box = ui.input(placeholder=placeholder).props("outlined autofocus").classes("w-80")
            box.on("keydown.enter", lambda: answer(box.value or ""))
            ui.button("Comprobar", icon="check", on_click=lambda: answer(box.value or "")).props(
                "unelevated color=primary no-caps"
            )

    def answer(typed: str) -> None:
        if st.mode == "num_palabra":
            ok = training.check_major_word(st.number, typed)
            detail = f"«{typed.strip()}» codifica {word_to_digits(typed) or '—'}; ejemplo: {st.word} = {st.number}."
        else:
            ok = "".join(c for c in typed if c.isdigit()) == st.number
            detail = f"«{st.word}» codifica {st.number}."
        st.correct += int(ok)
        st.index += 1
        stage.clear()
        with stage, ui.card().classes("mv-card w-full p-6 items-center gap-3 mv-pop"):
            ui.icon("check_circle" if ok else "cancel", color="positive" if ok else "negative").classes("text-6xl")
            ui.label("¡Correcto!" if ok else "Casi").classes("mv-h2")
            ui.label(detail).classes("mv-muted")
            last = st.index >= MAJOR_ROUND
            ui.button(
                "Ver resumen" if last else "Siguiente",
                icon="flag" if last else "arrow_forward",
                on_click=finish if last else ask,
            ).props("unelevated color=primary no-caps")

    def finish() -> None:
        seconds = round(time.monotonic() - st.started)
        _save("sistema_mayor", st.correct, 2, {"segundos": seconds, "modo": st.mode, "preguntas": MAJOR_ROUND})
        refresh_best()
        stage.clear()
        _summary(stage, f"{st.correct} aciertos de {MAJOR_ROUND}", [f"Tiempo: {seconds} s"], new_round)

    mode.on_value_change(lambda: new_round())
    new_round()


# --------------------------------------------------------------------------- 3. pares asociados
@dataclass
class PairsState:
    n: int = 6
    pairs: list[tuple[str, str]] = field(default_factory=list)
    timer: ui.timer | None = None


def _pairs_game() -> None:
    st = PairsState()
    refresh_best = _best_header("pares")
    stage = ui.column().classes("w-full gap-4")

    def stop_timer() -> None:
        if st.timer is not None:
            st.timer.cancel()
            st.timer = None

    def setup() -> None:
        stop_timer()
        stage.clear()
        with stage, ui.card().classes("mv-card w-full p-6 gap-4"):
            ui.label("¿Cuántos pares quieres memorizar?").classes("mv-h2")
            slider = ui.slider(min=4, max=10, step=1, value=st.n).props("label-always markers color=primary")
            ui.label(f"Verás todos a la vez durante {SECONDS_PER_PAIR:.0f} s por par.").classes("mv-muted text-sm")
            ui.button("Empezar", icon="play_arrow", on_click=lambda: begin(int(slider.value))).props(
                "unelevated color=primary no-caps"
            )

    def begin(n: int) -> None:
        stop_timer()
        st.n = n
        st.pairs = training.word_pairs(n)
        total = SECONDS_PER_PAIR * n
        elapsed = [0.0]
        stage.clear()
        with stage:
            ui.label("Consejo: une cada par en una escena absurda, con acción y exageración.").classes("mv-hook w-full")
            with ui.row().classes("w-full gap-3"):
                for a, b in st.pairs:
                    with ui.card().classes("mv-card p-4 items-center min-w-[10rem] flex-1 mv-pop"):
                        ui.label(a).classes("mv-h2")
                        ui.icon("link", color="primary")
                        ui.label(b).classes("mv-h2")
            bar = _countdown_bar()

            def tick(bar: ui.linear_progress = bar, elapsed: list[float] = elapsed, total: float = total) -> None:
                elapsed[0] += TICK
                bar.value = max(0.0, 1 - elapsed[0] / total)
                if elapsed[0] >= total:
                    stop_timer()
                    recall()

            st.timer = ui.timer(TICK, tick)

    def recall() -> None:
        order = [a for a, _ in st.pairs]
        random.shuffle(order)
        boxes: dict[str, ui.input] = {}
        stage.clear()
        with stage, ui.card().classes("mv-card w-full p-6 gap-3"):
            ui.label("¿Con qué palabra iba cada una?").classes("mv-h2")
            for a in order:
                boxes[a] = ui.input(label=a).props("outlined dense").classes("w-80")
            ui.button("Comprobar", icon="check", on_click=lambda: check(boxes)).props(
                "unelevated color=primary no-caps"
            )

    def check(boxes: dict[str, ui.input]) -> None:
        answers = {a: box.value or "" for a, box in boxes.items()}
        score = training.score_pairs(st.pairs, answers)
        _save("pares", score, st.n, {"pares": st.n, "aciertos": score})
        refresh_best()
        stage.clear()
        with stage, ui.card().classes("mv-card w-full p-6 gap-2 mv-pop"):
            ui.label(f"{score} de {st.n} pares").classes("mv-h2")
            for a, b in st.pairs:
                ok = answers.get(a, "").strip().lower() == b.lower()
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check_circle" if ok else "cancel", color="positive" if ok else "negative")
                    ui.label(f"{a} → {b}" + ("" if ok else f"  (escribiste: {answers.get(a, '').strip() or '—'})"))
        _summary(stage, f"Puntaje: {score}", [f"{st.n} pares · {round(100 * score / st.n)} % de acierto"], setup)

    setup()


# --------------------------------------------------------------------------- página
def view() -> None:
    page_title("Gimnasio mental", "Entrena memoria de trabajo y los códigos que usan tus ganchos.", "fitness_center")
    with ui.tabs().props("no-caps align=left active-color=primary") as tabs:
        for key, (title, icon, _hint) in training.GAMES.items():
            ui.tab(key, label=title, icon=icon)
    with ui.tab_panels(tabs, value="digitos").classes("w-full bg-transparent"):
        with ui.tab_panel("digitos").classes("gap-4"):
            _digits_game()
        with ui.tab_panel("sistema_mayor").classes("gap-4"):
            _major_game()
        with ui.tab_panel("pares").classes("gap-4"):
            _pairs_game()
