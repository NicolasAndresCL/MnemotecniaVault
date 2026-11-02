"""El método: por qué funciona la app (ciencia del aprendizaje) y cómo usarla cada día."""

from __future__ import annotations

from fsrs.scheduler import DEFAULT_PARAMETERS
from nicegui import ui

from app.config import get_settings
from app.models import TECHNIQUES
from app.ui.widgets import page_title

STABILITIES = (1, 5, 20)  # días: estabilidad S de las tres curvas
HORIZON_DAYS = 30


# Curva de olvido de FSRS-6 (la de la librería `fsrs` instalada): R(t) = (1 + F·t/S)^-d, con d = w20
# (decaimiento entrenable, 0,1542 por defecto) y F = 0,9^(-1/d) - 1 para que R(S) = 0,9 exactamente.
DECAY = DEFAULT_PARAMETERS[20]
FACTOR = 0.9 ** (-1 / DECAY) - 1


def retention(t: float, stability: float) -> float:
    """Probabilidad de recordar a los `t` días con estabilidad `stability` (FSRS-6); con t = S da 0,9."""
    return (1 + FACTOR * t / stability) ** -DECAY


def _forgetting_chart() -> None:
    days = list(range(HORIZON_DAYS + 1))
    ui.echart(
        {
            "tooltip": {"trigger": "axis"},
            "legend": {"top": 0},
            "grid": {"left": 48, "right": 16, "top": 40, "bottom": 36},
            "xAxis": {"type": "category", "data": days, "name": "días", "nameLocation": "middle", "nameGap": 24},
            "yAxis": {"type": "value", "min": 0, "max": 100, "axisLabel": {"formatter": "{value} %"}},
            "series": [
                {
                    "name": f"S = {s} d",
                    "type": "line",
                    "smooth": True,
                    "showSymbol": False,
                    "data": [round(100 * retention(t, s), 1) for t in days],
                }
                for s in STABILITIES
            ],
        }
    ).classes("w-full h-72")


def _card(icon: str, title: str, check: str):
    """Tarjeta de sección: devuelve el contexto para llenar el cuerpo; al salir añade el «Pruébate»."""
    return _SectionCard(icon, title, check)


class _SectionCard:
    def __init__(self, icon: str, title: str, check: str) -> None:
        self.icon, self.title, self.check = icon, title, check
        self._card = ui.card().classes("mv-card w-full p-5 gap-3")

    def __enter__(self) -> _SectionCard:
        self._card.__enter__()
        with ui.row().classes("items-center gap-3"):
            ui.icon(self.icon, color="primary").classes("text-3xl")
            ui.label(self.title).classes("mv-h2")
        return self

    def __exit__(self, *exc: object) -> None:
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.icon("quiz", color="warning")
            ui.label(f"Pruébate: {self.check}").classes("mv-muted")
        self._card.__exit__(*exc)


def _text(text: str) -> None:
    ui.label(text).classes("leading-relaxed")


def view() -> None:
    retention_goal = f"{get_settings().desired_retention:.2f}".replace(".", ",")
    page_title("El método", "Por qué funciona esta app y cómo sacarle partido cada día.", "school")

    with _card(
        "show_chart",
        "La curva del olvido",
        "¿Por qué a los 30 días recuerdas más de algo repasado muchas veces que de algo visto una sola vez?",
    ):
        _text(
            "Hermann Ebbinghaus mostró en 1885 que el olvido es rápido al comienzo y se enlentece después. "
            "Cada repaso bien hecho hace la curva más plana: la memoria se vuelve más estable. "
            "El gráfico usa la curva de potencia de FSRS-6, R(t) = (1 + F·t/S)^-d (d = 0,1542 por defecto), donde S "
            "es la estabilidad en días: el tiempo que tarda la retención en bajar de 100 % a 90 %."
        )
        _forgetting_chart()

    with _card(
        "psychology_alt",
        "Recuerdo activo (efecto de prueba)",
        "¿Qué rinde más a largo plazo: releer tres veces la nota o intentar recordarla de memoria una vez?",
    ):
        _text(
            "Intentar recuperar la respuesta, aunque falles, fortalece la memoria más que releer. Por eso el repaso "
            "te pide pensar y escribir antes de mostrar la respuesta, y cada tarjeta es una pregunta, no un resumen."
        )

    with _card(
        "event_repeat",
        "Repaso espaciado y FSRS",
        "¿Qué significan estabilidad, dificultad y recuperabilidad, y por qué conviene repasar justo antes de olvidar?",
    ):
        _text(
            "Repasar justo cuando está por olvidarse da el mayor refuerzo por minuto invertido. FSRS modela cada "
            "tarjeta con tres cantidades: estabilidad (cuánto dura el recuerdo), dificultad (qué tan costosa es) y "
            "recuperabilidad (la probabilidad de recordarla hoy). Con eso agenda el próximo repaso para que la "
            f"retención no baje de tu objetivo, que aquí es {retention_goal}."
        )

    with _card(
        "shuffle",
        "Práctica intercalada",
        "¿Por qué la sesión mezcla mazos en lugar de estudiar uno completo y pasar al siguiente?",
    ):
        _text(
            "Mezclar temas obliga a identificar qué estrategia o dato corresponde a cada pregunta. Se siente más "
            "difícil que estudiar por bloques, y justamente por eso se aprende mejor. Deja el repaso en modo "
            "«todos los mazos» salvo que prepares una prueba específica."
        )

    with _card(
        "image",
        "Codificación dual e imagen absurda",
        "¿Por qué una escena exagerada y con movimiento se recuerda mejor que una frase neutra?",
    ):
        _text(
            "Según la teoría de la codificación dual, una idea guardada como palabra y como imagen tiene dos "
            "caminos de recuperación. Las imágenes vívidas, exageradas y con acción son más distintivas, y lo "
            "distintivo se encuentra mejor. El gancho funciona si conecta con lo que quieres recordar, no solo "
            "por ser extraño."
        )

    with _card(
        "record_voice_over",
        "Elaboración (técnica Feynman)",
        "¿Puedes explicar el concepto en dos frases a alguien que no lo conoce, sin mirar la nota?",
    ):
        _text(
            "Explicar con tus propias palabras revela lo que solo reconocías. Si te trabas, esa es la brecha: "
            "vuelve a la fuente, corrige y explica de nuevo. Las tarjetas de resumen de la app existen para esto."
        )

    with _card(
        "table_chart",
        "Qué técnica para qué dato",
        "¿Qué técnica usarías para un puerto, una lista cerrada de pasos y un concepto abstracto?",
    ):
        ui.table(
            columns=[
                {"name": "t", "label": "Técnica", "field": "t", "align": "left"},
                {"name": "p", "label": "Sirve para", "field": "p", "align": "left"},
            ],
            rows=[{"t": name, "p": use} for name, use in TECHNIQUES.values()],
            row_key="t",
        ).props("flat dense").classes("w-full")

    with _card(
        "today",
        "Tu rutina diaria",
        "¿En qué orden harías hoy repaso, nuevas, gimnasio y ganchos, y por qué las vencidas van primero?",
    ):
        with ui.column().classes("gap-2"):
            for n, step in enumerate(
                (
                    "Repaso de las tarjetas vencidas: son las que más se están olvidando.",
                    "Tarjetas nuevas, con el cupo diario que tengas configurado.",
                    "Gimnasio mental, 5 minutos: dígitos, sistema mayor o pares.",
                    "Crear ganchos para las tarjetas que fallaste 2 veces o más.",
                ),
                start=1,
            ):
                with ui.row().classes("items-center gap-3 no-wrap"):
                    ui.badge(str(n), color="primary").classes("text-base")
                    _text(step)
        with ui.row().classes("gap-3"):
            for label, icon, path in (
                ("Ir al repaso", "bolt", "/repaso"),
                ("Ir al gimnasio", "fitness_center", "/gimnasio"),
                ("Crear ganchos", "anchor", "/ganchos"),
            ):
                ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)).props(
                    "unelevated color=primary no-caps"
                )
