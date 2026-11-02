"""Importador del seed de CmdVault: una tarjeta `comando` por comando, un mazo por categoría."""

from __future__ import annotations

import json
from pathlib import Path

from app.importers.base import CardDraft, ImportReport, make_key, slugify

MAX_EXAMPLES = 2


def _lang(slug: str) -> str:
    """Lenguaje de la valla de código según la categoría (mapeo simple)."""
    if slug.startswith("windows"):
        return "powershell"
    if slug in ("mysql", "postgres", "postgresql", "sql"):
        return "sql"
    if slug == "mongodb":
        return "javascript"
    return "bash"


def _fence(code: str, lang: str) -> str:
    ticks = "````" if "```" in code else "```"
    return f"{ticks}{lang}\n{code.strip()}\n{ticks}"


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _card(slug: str, name: str, cmd: dict) -> CardDraft | None:
    title, command = _text(cmd.get("title")), _text(cmd.get("command"))
    if not title or not command:
        return None
    lang = _lang(slug)
    where = " › ".join(p for p in (_text(cmd.get("section")), _text(cmd.get("topic"))) if p)
    front = f"**{title}**"
    if _text(cmd.get("description")):
        front += f"\n\n{_text(cmd['description'])}"
    if where:
        front += f"\n\n_{where}_"
    front += "\n\n¿Qué comando lo hace?"
    back = _fence(command, lang)
    examples = [e for e in (cmd.get("examples") or []) if isinstance(e, dict) and _text(e.get("code"))]
    for ex in examples[:MAX_EXAMPLES]:
        desc = _text(ex.get("description"))
        back += (f"\n\n- {desc}" if desc else "") + f"\n\n{_fence(_text(ex['code']), lang)}"
    raw_tags = [*(cmd.get("tags") or []), cmd.get("level"), *(cmd.get("roadmap") or [])]
    tags = tuple(dict.fromkeys(t.strip() for t in raw_tags if isinstance(t, str) and t.strip()))
    return CardDraft(
        deck_slug="cmd-" + slug,
        deck_name="Comandos · " + name,
        deck_source="cmdvault",
        key=make_key("cmdvault", slug, slugify(title)),
        kind="comando",
        front=front,
        back=back,
        context=f"CmdVault › {name}" + (f" › {where}" if where else ""),
        tags=tags,
    )


def parse_cmdvault(seed_dir: Path) -> tuple[list[CardDraft], ImportReport]:
    report = ImportReport(source="cmdvault")
    drafts: list[CardDraft] = []
    seed_dir = Path(seed_dir)
    if not seed_dir.is_dir():
        report.errors.append(f"{seed_dir}: la carpeta del seed no existe")
        return drafts, report
    seen: set[tuple[str, str]] = set()
    for path in sorted(seed_dir.glob("*.json")):
        report.files_seen += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            category = data["category"]
            slug = slugify(str(category["slug"]))
            name = _text(category.get("name")) or slug
            for cmd in data.get("commands") or []:
                draft = _card(slug, name, cmd) if isinstance(cmd, dict) else None
                if draft is None:
                    report.errors.append(f"{path.name}: comando sin título o sin comando")
                    continue
                if (draft.deck_slug, draft.key) in seen:  # mismo título repetido en la categoría
                    continue
                seen.add((draft.deck_slug, draft.key))
                drafts.append(draft)
        except Exception as exc:  # noqa: BLE001 - un JSON malo no debe tumbar la importación
            report.errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
    report.drafts = len(drafts)
    return drafts, report
