"""Importador del vault de Obsidian: notas → definiciones, tablas, «Pruébate», resúmenes y cloze."""

from __future__ import annotations

import os
import re
from pathlib import Path

from app.importers.base import CardDraft, ImportReport, has_secret, make_key, slugify
from app.importers.markdown import (
    Block,
    clean_inline,
    cloze_pairs,
    first_h1,
    frontmatter_tags,
    is_trivial_term,
    iter_blocks,
    parse_table,
    split_frontmatter,
    strip_bold,
)

SKIP_DIRS = frozenset({"_sistema", ".obsidian", ".trash"})
SKIP_ROOT_DIRS = frozenset({"04 Archivo"})  # carpeta inactiva del método PARA
SKIP_FILES = frozenset(
    {"aprendizaje.md", "memory.md", "pendientes.md", "changelog.md", "claude.md", "agents.md", "skill.md"}
)
MAX_BYTES = 400 * 1024
MAX_TABLE_ROWS = 12
MAX_TABLES = 3
MAX_CLOZE = 15
INDEX_TAG = "indice-generado"

_PARA_RE = re.compile(r"^0\d\s+(.+)$")
_DEF_RE = re.compile(r"^\*\*(?P<t>[^*]{1,80}?)\*\*(?P<sep>\s*[:：]|\s*[—–=]|\s+-\s)?\s*(?P<d>\S.*)$")
_DEF_COLON_IN_BOLD_RE = re.compile(r"^\*\*(?P<t>[^*]{1,80}?):\*\*\s*(?P<d>\S.*)$")
_RESUMEN_RE = re.compile(r"(?is)^\*\*Resumen:?\*\*:?\s*(?P<r>.+)$")


def _deck_for(parts: tuple[str, ...]) -> tuple[str, str | None]:
    """(nombre_del_mazo, etiqueta_PARA|None) a partir de las partes de la ruta relativa."""
    if len(parts) == 1:
        return "Vault", None
    m = _PARA_RE.match(parts[0])
    para = m.group(1).strip() if m else None
    if len(parts) == 2:
        return para or parts[0], para
    return parts[1], para


def _definition(text: str) -> tuple[str, str] | None:
    m = _DEF_COLON_IN_BOLD_RE.match(text)
    if m:
        term, definition = m.group("t"), m.group("d")
    else:
        m = _DEF_RE.match(text)
        if not m or not m.group("sep"):
            return None
        term, definition = m.group("t"), m.group("d")
    term = term.strip().rstrip(":").strip()
    definition = (
        strip_bold(clean_inline(definition)).strip() if definition.count("**") % 2 else clean_inline(definition)
    )
    if (
        not term
        or len(term.split()) > 5
        or is_trivial_term(term)
        or re.search(r"\d+$", term)
        or definition.endswith(":")
        or not 15 <= len(definition) <= 600
        or len(definition.split()) < 4
    ):
        return None
    return term, definition


class _Collector:
    """Acumula borradores de un mazo garantizando keys únicas y descartando secretos."""

    def __init__(self, report: ImportReport) -> None:
        self.report = report
        self.drafts: list[CardDraft] = []
        self._seen: set[tuple[str, str]] = set()

    def add(self, draft_args: dict, key_parts: tuple[str, ...], front: str, back: str) -> None:
        if has_secret(front, back):
            self.report.skipped_secret += 1
            return
        key = make_key(*key_parts)
        n = 1
        while (draft_args["deck_slug"], key) in self._seen:
            n += 1
            key = make_key(*key_parts, str(n))
        self._seen.add((draft_args["deck_slug"], key))
        self.drafts.append(CardDraft(key=key, front=front, back=back, **draft_args))


def _note_cards(rel: str, text: str, col: _Collector) -> bool:
    """Genera las tarjetas de una nota. Devuelve False si la nota se salta (índice generado)."""
    meta, body = split_frontmatter(text)
    tags = frontmatter_tags(meta)
    if INDEX_TAG in tags or re.search(rf"(?<![\w-])#{INDEX_TAG}\b", body):
        return False

    parts = tuple(rel.split("/"))
    deck_name, para = _deck_for(parts)
    title = str(meta.get("title") or "").strip() or first_h1(body) or Path(rel).stem
    all_tags = tuple(dict.fromkeys([*tags, *([slugify(para)] if para else [])]))
    base = {"deck_slug": "obsidian-" + slugify(deck_name), "deck_name": deck_name, "deck_source": "obsidian"}

    def args(kind: str, heading: str) -> dict:
        return {**base, "kind": kind, "context": f"{rel} › {heading}" if heading else rel, "tags": all_tags}

    heading = ""
    section_blocks: list[Block] = []
    cloze_budget = MAX_CLOZE
    tables_done = 0
    for block in iter_blocks(body):
        if block.kind == "heading":
            heading, section_blocks = block.text, []
            continue
        if block.kind == "table":
            if tables_done < MAX_TABLES and _table_cards(rel, heading, block, args("tabla", heading), col):
                tables_done += 1
        elif block.kind == "pruebate":
            back = "\n\n".join("\n".join(b.lines) for b in section_blocks if b.kind != "heading")
            back = clean_inline(back).strip()[:1200]
            if len(block.text) >= 10 and back:
                col.add(args("pruebate", heading), ("obsidian", rel, "pruebate", block.text), block.text, back)
        elif block.kind == "quote":
            m = _RESUMEN_RE.match(block.text.strip())
            if m:
                resumen = clean_inline(re.sub(r"\s*\n\s*", " ", m.group("r"))).strip()
                if resumen:
                    front = f"Resume con tus palabras la nota «{title}»"
                    col.add(args("resumen", heading), ("obsidian", rel, "resumen", title), front, resumen)
        elif block.kind in ("item", "para"):
            definition = _definition(block.text)
            if definition:
                term, d = definition
                col.add(
                    args("definicion", heading),
                    ("obsidian", rel, "definicion", heading, term),
                    f"¿Qué es **{term}**?",
                    d,
                )
            elif cloze_budget > 0:
                for sentence, front, term in cloze_pairs(block.text, max_cards=cloze_budget):
                    col.add(args("cloze", heading), ("obsidian", rel, "cloze", sentence, term), front, term)
                    cloze_budget -= 1
        if block.kind != "heading":
            section_blocks.append(block)
    return True


def _mostly_numeric(cell: str) -> bool:
    """Celdas que son casi solo cifras/símbolos (métricas, versiones): no sirven como pregunta ni respuesta."""
    letters = sum(c.isalpha() for c in cell)
    return letters < 3 and len(cell) > 0


def _technical_id(cell: str) -> bool:
    """Celda que parece ruta, archivo, llamada o identificador técnico (poco estudiable como pregunta)."""
    c = cell.strip("` ")
    if any(t in c for t in ("/", "\\", ".py", ".md", "()")):
        return True
    if " " in c:
        return False
    return "_" in c or bool(re.fullmatch(r"[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+", c))


def _table_cards(rel: str, heading: str, block: Block, draft_args: dict, col: _Collector) -> int:
    """Añade las filas válidas de la tabla y devuelve cuántas tarjetas generó."""
    added = 0
    table = parse_table(block.lines)
    if table is None or not 2 <= len(table.header) <= 6 or len(table.rows) < 2:
        return 0
    h = [strip_bold(c) for c in table.header]
    if not h[0] or not h[1]:
        return 0
    for row in table.rows[:MAX_TABLE_ROWS]:
        cells = [strip_bold(c) for c in row]
        if not cells[0] or not cells[1] or cells[0] in ("-", "—") or cells[1] in ("-", "—") or len(cells[0]) > 120:
            continue
        if cells[0] == cells[1] or _mostly_numeric(cells[1]) or _mostly_numeric(cells[0]):
            continue
        if _technical_id(cells[0]):
            continue
        front = f"**{h[0]}: {cells[0]}** → ¿{h[1]}?"
        back = cells[1]
        extras = [f"- **{h[i]}**: {cells[i]}" for i in range(2, len(h)) if h[i] and cells[i]]
        if extras:
            back += "\n\n" + "\n".join(extras)
        col.add(draft_args, ("obsidian", rel, "tabla", heading, cells[0]), front, back)
        added += 1
    return added


def parse_vault(root: Path) -> tuple[list[CardDraft], ImportReport]:
    """Recorre el vault (solo lectura) y devuelve los borradores + el informe."""
    report = ImportReport(source="obsidian")
    col = _Collector(report)
    root = Path(root)
    if not root.is_dir():
        report.errors.append(f"{root}: la carpeta del vault no existe")
        return [], report
    for dirpath, dirnames, filenames in os.walk(root):
        skip = SKIP_DIRS | (SKIP_ROOT_DIRS if Path(dirpath) == root else frozenset())
        dirnames[:] = sorted(d for d in dirnames if d not in skip and not d.endswith("_files"))
        for name in sorted(filenames):
            if not name.lower().endswith(".md"):
                continue
            report.files_seen += 1
            path = Path(dirpath) / name
            if name.lower() in SKIP_FILES:
                continue
            rel = path.relative_to(root).as_posix()
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                _note_cards(rel, text, col)
            except Exception as exc:  # noqa: BLE001 - una nota mala no debe tumbar la importación
                report.errors.append(f"{rel}: {type(exc).__name__}: {exc}")
    report.drafts = len(col.drafts)
    return col.drafts, report
