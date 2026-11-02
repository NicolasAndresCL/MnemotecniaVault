"""Importador de `aprendizaje.md` de cada proyecto: lecciones por tecnología + cloze."""

from __future__ import annotations

from pathlib import Path

from app.importers.base import CardDraft, ImportReport, has_secret, make_key, slugify
from app.importers.markdown import (
    BOLD_RE,
    clean_inline,
    cloze_pairs,
    iter_entries,
    split_frontmatter,
    split_sections,
    strip_bold,
    strip_code_blocks,
)

SKIP_DIRS = frozenset({"env", "venv", ".venv", "node_modules", ".git", "__pycache__"})
MAX_BACK = 1500
MAX_CLOZE = 10


def _hook(title: str, body: str) -> str:
    """Gancho de una entrada: título `###`, primera negrita razonable o primeras ~12 palabras."""
    if title:
        return title
    for m in BOLD_RE.finditer(clean_inline(body)):
        t = m.group(1).strip().strip(".:")
        if 3 <= len(t) <= 100:
            return t
    words = strip_bold(clean_inline(body)).split()
    return " ".join(words[:12]) + ("…" if len(words) > 12 else "")


def _file_cards(project: str, text: str, report: ImportReport) -> list[CardDraft]:
    _, body = split_frontmatter(text)
    deck = {
        "deck_slug": "lecciones-" + slugify(project),
        "deck_name": "Lecciones · " + project,
        "deck_source": "proyecto",
    }
    seen: set[str] = set()
    cards: list[CardDraft] = []

    def add(kind: str, key_parts: tuple[str, ...], front: str, back: str, context: str, tags: tuple[str, ...]) -> None:
        if has_secret(front, back):
            report.skipped_secret += 1
            return
        key, n = make_key(*key_parts), 1
        while key in seen:
            n += 1
            key = make_key(*key_parts, str(n))
        seen.add(key)
        cards.append(CardDraft(key=key, kind=kind, front=front, back=back, context=context, tags=tags, **deck))

    clozes = 0
    for section in split_sections(body.splitlines(), 2):
        tech = section.heading
        if not tech:
            continue
        tags = (slugify(tech), slugify(project))
        context = f"{project}/aprendizaje.md › {tech}"
        for title, entry in iter_entries(section.lines):
            hook = _hook(title, entry)
            back = clean_inline(entry)[:MAX_BACK].strip()
            front = f"**{tech}** · ¿qué trampa o lección hay detrás de: «{hook}»?"
            add("leccion", ("proyecto", project, tech, hook), front, back, context, tags)
            if clozes < MAX_CLOZE:
                for sentence, cfront, term in cloze_pairs(strip_code_blocks(entry), max_cards=MAX_CLOZE - clozes):
                    add("cloze", ("proyecto", project, tech, "cloze", sentence, term), cfront, term, context, tags)
                    clozes += 1
    return cards


def parse_projects(root: Path) -> tuple[list[CardDraft], ImportReport]:
    report = ImportReport(source="proyecto")
    drafts: list[CardDraft] = []
    root = Path(root)
    if not root.is_dir():
        report.errors.append(f"{root}: la carpeta de proyectos no existe")
        return drafts, report
    for project_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in SKIP_DIRS):
        path = project_dir / "aprendizaje.md"
        if not path.is_file():
            continue
        report.files_seen += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            drafts.extend(_file_cards(project_dir.name, text, report))
        except Exception as exc:  # noqa: BLE001 - un archivo malo no debe tumbar la importación
            report.errors.append(f"{project_dir.name}/aprendizaje.md: {type(exc).__name__}: {exc}")
    report.drafts = len(drafts)
    return drafts, report
