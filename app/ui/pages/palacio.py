"""Palacio de la memoria (método de loci): estaciones de un lugar conocido que anclan tarjetas en orden."""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from app.db import session_scope
from app.mnemonics import DEFAULT_PALACE_STATIONS
from app.repository import create_palace, delete_palace, get_palace, list_palaces, search_cards, update_locus
from app.ui.widgets import empty_state, md, page_title, run_safe


@dataclass
class State:
    palace_id: int | None = None
    walking: bool = False
    step: int = 0
    revealed: bool = False


def view() -> None:
    page_title(
        "Palacio de la memoria",
        "Recorre un lugar que conoces de memoria; en cada estación, una escena absurda guarda un concepto.",
        "castle",
    )
    st = State()
    with session_scope() as s:
        palaces = list_palaces(s)
        if palaces:
            st.palace_id = palaces[0].id

    top = ui.row().classes("w-full items-center gap-3")
    body = ui.column().classes("w-full gap-4")

    def render_top() -> None:
        top.clear()
        with session_scope() as s:
            opts = {p.id: f"{p.name} ({len(p.loci)} estaciones)" for p in list_palaces(s)}
        with top:
            if opts:
                ui.select(opts, value=st.palace_id, label="Palacio", on_change=lambda e: select(e.value)).props(
                    "outlined dense"
                ).classes("min-w-[18rem]")
                ui.button("Recorrido sin mirar", icon="directions_walk", on_click=lambda: walk(True)).props(
                    "unelevated color=primary no-caps"
                )
            ui.space()
            ui.button("Nuevo palacio", icon="add_home", on_click=new_palace).props("outline color=primary no-caps")

    def select(pid: int) -> None:
        st.palace_id, st.walking = pid, False
        render()

    def walk(on: bool) -> None:
        st.walking, st.step, st.revealed = on, 0, False
        render()

    def render() -> None:
        body.clear()
        with body:
            if st.palace_id is None:
                empty_state(
                    "castle",
                    "Construye tu primer palacio",
                    "Usa tu casa: 10–12 estaciones en el orden en que las recorres. Una escena por concepto.",
                )
                return
            with session_scope() as s:
                palace = get_palace(s, st.palace_id)
                loci = [
                    {
                        "id": lc.id,
                        "pos": lc.position,
                        "place": lc.place,
                        "scene": lc.scene,
                        "card_id": lc.card_id,
                        "front": lc.card.front if lc.card else "",
                        "back": lc.card.back if lc.card else "",
                    }
                    for lc in palace.loci
                ]
                name, desc = palace.name, palace.description
            if st.walking:
                walk_view(name, loci)
            else:
                edit_view(name, desc, loci)

    def edit_view(name: str, desc: str, loci: list[dict]) -> None:
        with ui.row().classes("w-full items-center"):
            ui.label(name).classes("mv-h2")
            if desc:
                ui.label(desc).classes("mv-muted")
            ui.space()
            ui.button(icon="delete", on_click=lambda: remove()).props("flat round color=negative").tooltip(
                "Borrar palacio"
            )
        with ui.timeline(side="right").classes("w-full"):
            for lc in loci:
                with ui.timeline_entry(
                    title=f"{lc['pos']}. {lc['place']}",
                    icon="place",
                    color="primary" if lc["card_id"] else "grey",
                ):
                    station(lc)

    def station(lc: dict) -> None:
        with ui.card().classes("mv-card w-full p-4 gap-3"):
            if lc["front"]:
                with ui.row().classes("w-full items-start no-wrap gap-2"):
                    ui.icon("link", color="primary")
                    with ui.column().classes("flex-1 gap-0"):
                        md(lc["front"])
                    ui.button(icon="link_off", on_click=lambda i=lc["id"]: anchor(i, None)).props(
                        "flat round dense"
                    ).tooltip("Desanclar")
            else:
                search = ui.input(placeholder="Busca una tarjeta para anclarla aquí…").props("outlined dense")
                search.classes("w-full")
                found = ui.column().classes("w-full gap-1")

                def do_search(q=search, box=found, lid=lc["id"]) -> None:  # noqa: ANN001
                    box.clear()
                    with session_scope() as s:
                        cards = [
                            (c.id, c.front.replace("**", "")[:110]) for c in search_cards(s, q.value or "", limit=6)
                        ]
                    with box:
                        for cid, front in cards:
                            ui.item(front, on_click=lambda c=cid, li=lid: anchor(li, c)).props("clickable dense")

                search.on("keydown.enter", do_search)
            scene = ui.textarea("Escena: exagerada, en movimiento, con ruido u olor", value=lc["scene"]).props(
                "outlined autogrow dense"
            )
            scene.classes("w-full")
            scene.on("blur", lambda e, i=lc["id"], sc=scene: save_scene(i, sc.value))

    def anchor(locus_id: int, card_id: int | None) -> None:
        with session_scope() as s:
            update_locus(s, locus_id, card_id=card_id)
        render()

    def save_scene(locus_id: int, scene: str) -> None:
        with session_scope() as s:
            update_locus(s, locus_id, scene=scene or "")
        ui.notify("Escena guardada", type="positive", timeout=900)

    def remove() -> None:
        with session_scope() as s:
            delete_palace(s, st.palace_id)
            rest = list_palaces(s)
        st.palace_id = rest[0].id if rest else None
        render_top()
        render()

    def walk_view(name: str, loci: list[dict]) -> None:
        anchored = [lc for lc in loci if lc["card_id"]] or loci
        if st.step >= len(anchored):
            with ui.card().classes("mv-card w-full p-8 items-center gap-3 mv-pop"):
                ui.icon("emoji_events", color="warning").classes("text-7xl")
                ui.label("Recorrido completo").classes("mv-h1")
                ui.label("Repite el recorrido mañana al despertar, sin mirar (calendario de la skill).").classes(
                    "mv-muted"
                )
                ui.button("Volver a editar", on_click=lambda: walk(False)).props("outline color=primary no-caps")
            return
        lc = anchored[st.step]
        ui.linear_progress(value=st.step / len(anchored), show_value=False).props("rounded color=primary")
        with ui.card().classes("mv-card mv-study w-full p-8 gap-4 mv-pop"):
            ui.label(f"Estación {lc['pos']} · {name}").classes("mv-chip-tech")
            ui.label(lc["place"]).classes("mv-h1")
            ui.label("Cierra los ojos y entra. ¿Qué escena hay aquí? ¿Qué concepto guarda?").classes("mv-muted")
            if st.revealed:
                with ui.column().classes("w-full gap-3 mv-reveal"):
                    if lc["scene"]:
                        with ui.element("div").classes("mv-hook w-full"):
                            md(lc["scene"])
                    if lc["front"]:
                        md(lc["front"])
                        ui.separator()
                        md(lc["back"])
                with ui.row().classes("gap-2"):
                    ui.button("Siguiente estación", icon="arrow_forward", on_click=lambda: advance()).props(
                        "unelevated color=primary no-caps"
                    )
            else:
                ui.button("Revelar", icon="visibility", on_click=lambda: reveal()).props(
                    "unelevated color=primary no-caps"
                )
            ui.button("Salir del recorrido", on_click=lambda: walk(False)).props("flat no-caps")

    def reveal() -> None:
        st.revealed = True
        render()

    def advance() -> None:
        st.step, st.revealed = st.step + 1, False
        render()

    def new_palace() -> None:
        with ui.dialog() as dlg, ui.card().classes("mv-card w-[36rem] max-w-[95vw] p-6 gap-3"):
            ui.label("Nuevo palacio").classes("mv-h2")
            name = ui.input("Nombre", value="Mi casa").props("outlined dense").classes("w-full")
            desc = ui.input("Para qué temario (p. ej. «Cátedra U3 Diseño de Software»)").props("outlined dense")
            desc.classes("w-full")
            stations = (
                ui.textarea(
                    "Estaciones en orden de recorrido (una por línea)", value="\n".join(DEFAULT_PALACE_STATIONS)
                )
                .props("outlined autogrow")
                .classes("w-full")
            )

            def _save() -> None:
                def _do() -> object:
                    with session_scope() as s:
                        return create_palace(
                            s, name.value or "", (stations.value or "").splitlines(), desc.value or ""
                        ).id

                pid = run_safe(_do, ok="Palacio creado: ancla una tarjeta por estación")
                if pid:
                    st.palace_id = int(pid)  # type: ignore[arg-type]
                    dlg.close()
                    render_top()
                    render()

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                ui.button("Crear", on_click=_save).props("unelevated color=primary no-caps")
        dlg.open()

    render_top()
    render()
