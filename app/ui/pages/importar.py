"""Importar: sincroniza el vault de Obsidian, CmdVault y las lecciones de los proyectos."""

from __future__ import annotations

from nicegui import run, ui

from app.importers.runner import configured_sources, run_import
from app.ui.widgets import SOURCE_META, md, page_title

HELP = """
Las fuentes se leen **en solo lectura** y se configuran por entorno:

| Variable | Fuente |
|---|---|
| `VAULT_PATH` | Vault de Obsidian (`C:\\dev\\learning_center`) |
| `CMDVAULT_SEED_PATH` | Seed de CmdVault (`CmdVault\\backend\\app\\seed\\data`) |
| `PROJECTS_PATH` | Carpeta de proyectos (busca `*/aprendizaje.md`) |

Reimportar es seguro: si corriges una nota, la tarjeta se **actualiza sin perder su progreso**; si la
borras, la tarjeta queda **suspendida** (vuelve si la nota reaparece).
"""

STAT_BADGES = (
    ("created", "nuevas", "positive"),
    ("updated", "actualizadas", "info"),
    ("unchanged", "sin cambios", "grey"),
    ("orphaned", "suspendidas (ya no están)", "warning"),
    ("restored", "recuperadas", "primary"),
)


def view() -> None:
    page_title(
        "Importar fuentes", "Tu conocimiento se convierte en tarjetas: definiciones, tablas, huecos y más.", "sync"
    )
    sources = configured_sources()

    async def go(only: str | None) -> None:
        results.clear()
        with results:
            spinner = ui.spinner("dots", size="xl", color="primary")
        data = await run.io_bound(run_import, only)
        spinner.delete()
        with results:
            for r in data:
                label, icon = SOURCE_META.get(r.source, (r.source, "sync"))
                with ui.card().classes("mv-card w-full p-4 gap-2 mv-pop"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon(icon, color="primary").classes("text-2xl")
                        ui.label(label).classes("mv-h2")
                        ui.label(f"{r.seconds} s".replace(".", ",")).classes("mv-muted text-sm")
                    if r.error:
                        ui.label(r.error).classes("text-negative")
                        continue
                    with ui.row().classes("gap-2"):
                        for k, txt, color in STAT_BADGES:
                            ui.badge(f"{r.stats.get(k, 0)} {txt}", color=color).props("outline")
                    if r.report:
                        ui.label(
                            f"{r.report.files_seen} archivos · {r.report.drafts} tarjetas generadas · "
                            f"{r.report.skipped_secret} descartadas por parecer secretos"
                        ).classes("text-sm mv-muted")
                        for err in r.report.errors[:5]:
                            ui.label(err).classes("text-xs text-negative")
        ui.notify("Importación terminada", type="positive")

    with ui.row().classes("w-full gap-4"):
        for key, (label, icon) in SOURCE_META.items():
            if key == "manual":
                continue
            path = sources.get(key)
            with ui.card().classes("mv-card flex-1 min-w-[16rem] p-5 gap-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon(icon, color="primary").classes("text-3xl")
                    ui.label(label).classes("mv-h2")
                ui.label(path or "Sin configurar").classes("text-xs font-mono mv-muted break-all")
                btn = ui.button("Importar", icon="download", on_click=lambda k=key: go(k))
                btn.props("outline color=primary no-caps").set_enabled(bool(path))
    ui.button("Importar todo", icon="sync", on_click=lambda: go(None)).props(
        "unelevated rounded size=lg color=primary no-caps"
    ).set_enabled(bool(sources))
    results = ui.column().classes("w-full gap-3")
    md(HELP)
