"""Temas visuales (misma convención de tonos que CmdVault: Eren, Luffy, Dark) y CSS global."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    dark: bool
    quasar: dict[str, str]  # primary/secondary/accent/positive/negative/info/warning
    css: dict[str, str]  # variables --mv-*
    heading_font: str
    tagline: str


THEMES: dict[str, Theme] = {
    "eren": Theme(
        key="eren",
        label="Eren · Titán Fundador",
        dark=True,
        # El Retumbar: hueso, cielo color brasa, tierra quemada y óxido.
        quasar={
            "primary": "#d9622b",
            "secondary": "#e8dcc4",
            "accent": "#a33a1f",
            "positive": "#7fa36b",
            "negative": "#c0392b",
            "info": "#c9a27a",
            "warning": "#e0a43a",
        },
        css={
            "bg": "#130d0a",
            "bg-image": (
                "radial-gradient(1100px 520px at 50% -15%, #5a2410 0%, transparent 60%),"
                "linear-gradient(180deg, #1c120d 0%, #130d0a 70%)"
            ),
            "surface": "#1f1611",
            "surface-2": "#2a1d16",
            "border": "#3d2a1f",
            "text": "#efe6d6",
            "muted": "#b8a58c",
            "code-bg": "#0d0907",
            "code-text": "#f1ece4",
            "glow": "rgba(217, 98, 43, .30)",
            "hero": "linear-gradient(135deg, #5a2410 0%, #2a1d16 55%, #1f1611 100%)",
        },
        heading_font="'Cinzel', Georgia, serif",
        tagline="Lo que no se repasa, se lo come el Retumbar del olvido.",
    ),
    "luffy": Theme(
        key="luffy",
        label="Luffy · Quinta Marcha",
        dark=False,
        # Gear 5 / Nika: blanco nube, morado del cielo, rojo del chaleco y dorado del sombrero.
        quasar={
            "primary": "#7c4dff",
            "secondary": "#e63946",
            "accent": "#ffbe0b",
            "positive": "#2ec4b6",
            "negative": "#e63946",
            "info": "#9d7bff",
            "warning": "#ffbe0b",
        },
        css={
            "bg": "#fbf8ff",
            "bg-image": (
                "radial-gradient(900px 420px at 85% -5%, #ffe8a3 0%, transparent 55%),"
                "radial-gradient(800px 500px at 0% 0%, #e9ddff 0%, transparent 60%),"
                "radial-gradient(600px 400px at 50% 110%, #ffffff 0%, transparent 70%)"
            ),
            "surface": "#ffffff",
            "surface-2": "#f4eeff",
            "border": "#e2d6ff",
            "text": "#2a1f3d",
            "muted": "#6b5d85",
            "code-bg": "#f6f1ff",
            "code-text": "#2a1f3d",
            "glow": "rgba(124, 77, 255, .28)",
            "hero": "linear-gradient(135deg, #ede4ff 0%, #fff3cf 60%, #ffffff 100%)",
        },
        heading_font="'Bangers', 'Inter', sans-serif",
        tagline="¡Libertad! Tu memoria, estirada como goma.",
    ),
    "dark": Theme(
        key="dark",
        label="Dark",
        dark=True,
        quasar={
            "primary": "#4f8cff",
            "secondary": "#8b5cf6",
            "accent": "#22d3ee",
            "positive": "#22c55e",
            "negative": "#ef4444",
            "info": "#38bdf8",
            "warning": "#f59e0b",
        },
        css={
            "bg": "#0e1015",
            "bg-image": "radial-gradient(1200px 600px at 10% -10%, #1b2440 0%, transparent 60%)",
            "surface": "#161a22",
            "surface-2": "#1d2230",
            "border": "#2a3142",
            "text": "#e6e8ee",
            "muted": "#9aa3b5",
            "code-bg": "#0b0d12",
            "code-text": "#e6e8ee",
            "glow": "rgba(79, 140, 255, .25)",
            "hero": "linear-gradient(135deg, #1b2440 0%, #161a22 70%)",
        },
        heading_font="'Inter', system-ui, sans-serif",
        tagline="Modo noche: foco total en recordar.",
    ),
}

DEFAULT_THEME = "eren"


def get_theme(key: str | None) -> Theme:
    return THEMES.get(key or "", THEMES[DEFAULT_THEME])


def css_variables(theme: Theme) -> str:
    body = "".join(f"--mv-{k}: {v};" for k, v in theme.css.items())
    return f":root {{ {body} --mv-heading: {theme.heading_font}; }}"


FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Bangers&family=Cinzel:wght@600;800'
    '&family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">'
)

BASE_CSS = """
body { background: var(--mv-bg); background-image: var(--mv-bg-image); background-attachment: fixed;
       color: var(--mv-text); font-family: 'Inter', system-ui, sans-serif; }
.q-header { background: color-mix(in srgb, var(--mv-surface) 80%, transparent) !important;
            backdrop-filter: blur(12px); border-bottom: 1px solid var(--mv-border); color: var(--mv-text); }
.q-drawer { background: var(--mv-surface) !important; border-right: 1px solid var(--mv-border); }
.mv-brand { font-family: var(--mv-heading); font-size: 1.55rem; letter-spacing: .04em; line-height: 1;
            background: linear-gradient(90deg, var(--q-primary), var(--q-warning)); -webkit-background-clip: text;
            background-clip: text; color: transparent; }
.mv-h1 { font-family: var(--mv-heading); font-size: 2.4rem; line-height: 1.05; letter-spacing: .02em; }
.mv-h2 { font-family: var(--mv-heading); font-size: 1.4rem; letter-spacing: .02em; }
.mv-muted { color: var(--mv-muted); }
.mv-card { background: var(--mv-surface) !important; border: 1px solid var(--mv-border); border-radius: 16px;
           color: var(--mv-text); box-shadow: none; transition: box-shadow .2s, transform .2s, border-color .2s; }
.mv-card:hover { box-shadow: 0 0 0 1px var(--q-primary), 0 12px 34px var(--mv-glow); }
.mv-link { cursor: pointer; }
.mv-link:hover { transform: translateY(-3px); }
.mv-hero { background: var(--mv-hero); border: 1px solid var(--mv-border); border-radius: 22px; position: relative;
           overflow: hidden; }
.mv-hero::after { content: ""; position: absolute; inset: -40% -10% auto auto; width: 420px; height: 420px;
                  background: radial-gradient(circle, var(--mv-glow) 0%, transparent 65%); pointer-events: none;
                  animation: mv-pulse 6s ease-in-out infinite; }
@keyframes mv-pulse { 0%,100% { transform: scale(1); opacity: .8 } 50% { transform: scale(1.15); opacity: 1 } }
.mv-stat { font-family: var(--mv-heading); font-size: 2.3rem; color: var(--q-primary); line-height: 1; }
.mv-flame { color: var(--q-warning); animation: mv-flicker 1.6s ease-in-out infinite; }
@keyframes mv-flicker { 0%,100% { transform: scale(1) rotate(-3deg) } 50% { transform: scale(1.12) rotate(3deg) } }
.mv-study { min-height: 280px; border-radius: 22px; }
.mv-front { font-size: 1.25rem; line-height: 1.55; }
.mv-reveal { animation: mv-flip .45s cubic-bezier(.2,.8,.2,1); transform-origin: top center; }
@keyframes mv-flip { from { transform: perspective(900px) rotateX(-80deg); opacity: 0 }
                     to { transform: perspective(900px) rotateX(0); opacity: 1 } }
.mv-pop { animation: mv-pop .35s ease-out; }
@keyframes mv-pop { 0% { transform: scale(.9); opacity: 0 } 100% { transform: scale(1); opacity: 1 } }
.mv-hook { border-left: 3px solid var(--q-warning); background: var(--mv-surface-2); padding: .55rem .85rem;
           border-radius: 8px; }
.mv-chip-tech { background: color-mix(in srgb, var(--q-primary) 18%, transparent); color: var(--q-primary);
                border-radius: 999px; padding: .1rem .6rem; font-size: .75rem; font-weight: 600; }
.mv-kbd { font-family: 'JetBrains Mono', monospace; font-size: .72rem; border: 1px solid var(--mv-border);
          border-bottom-width: 2px; border-radius: 5px; padding: 0 .3rem; opacity: .75; }
.mv-digits { font-family: 'JetBrains Mono', monospace; font-size: 2.6rem; letter-spacing: .35em; color: var(--q-primary); }
.mv-station { border-radius: 14px; border: 1px dashed var(--mv-border); }
.nicegui-markdown pre { background: var(--mv-code-bg); color: var(--mv-code-text); padding: .6rem; border-radius: 8px;
                        border: 1px solid var(--mv-border); white-space: pre-wrap; }
.nicegui-markdown code { font-family: 'JetBrains Mono', monospace; }
.nicegui-markdown table { border-collapse: collapse; }
.nicegui-markdown th, .nicegui-markdown td { border: 1px solid var(--mv-border); padding: .3rem .6rem; }
.nicegui-markdown a { color: var(--q-primary); }
.nicegui-markdown p:last-child { margin-bottom: 0; }
.q-field__native, .q-field__label, .q-item, .q-expansion-item { color: var(--mv-text); }
.q-menu, .q-dialog .q-card { background: var(--mv-surface); color: var(--mv-text); }
.q-table__card { background: var(--mv-surface) !important; color: var(--mv-text); }
"""
