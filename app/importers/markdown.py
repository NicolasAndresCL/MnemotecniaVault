"""Helpers compartidos de parseo de Markdown (solo stdlib + PyYAML para el frontmatter)."""

from __future__ import annotations

import re
import textwrap
from collections.abc import Iterator
from dataclasses import dataclass, field

import yaml

FRONTMATTER_RE = re.compile(r"\A﻿?---[ \t]*\r?\n(.*?)\r?\n(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)", re.DOTALL)
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ITEM_RE = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?(.*)$")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)*\|?\s*$")
HRULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
PRUEBATE_RE = re.compile(r"(?i)^\s*(?:>\s*)*(?:[-*+]\s+)?(?:\*\*Pr[uú]ébate:?\*\*:?|Pr[uú]ébate:)\s*(.+?)\s*$")
BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")

_DEFLINE_RE = re.compile(r"^\*\*[^*]{1,80}\*\*\s*(?:[:：—–=]|-\s)|^\*\*[^*]{1,80}:\*\*")
_WIKI_EMBED_RE = re.compile(r"!\[\[[^\]]*\]\]")
_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_WIKI_RE = re.compile(r"\[\[([^\]|]*)(?:\|([^\]]*))?\]\]")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_BR_RE = re.compile(r"(?i)<br\s*/?>")
_SENTENCE_SPLIT_RE = re.compile(r"(?:(?<=[.!?])|(?<=[.!?]\*\*))\s+(?=[A-ZÁÉÍÓÚÑ¿¡*`\"«(\d])")

# Etiquetas en negrita que no son conceptos (metadatos, avisos, marcadores de sección).
LABEL_TERMS = frozenset(
    {
        "nota", "notas", "ojo", "importante", "ejemplo", "ejemplos", "regla", "regla de uso", "pruébate",
        "pruebate", "resumen", "autor", "fecha", "versión", "version", "estado", "tags", "tag", "tipo",
        "cuándo", "cuando", "por qué", "porque", "cómo", "como", "qué", "que", "ver", "ver también",
        "advertencia", "cuidado", "tip", "atención", "atencion", "problema", "solución", "solucion",
        "causa", "síntoma", "sintoma", "arreglo", "prioridad", "origen", "fuente", "gancho", "paso", "pasos",
        "sí", "si", "no", "salida", "salida esperada", "comando", "comandos", "objetivo", "contexto",
    }
)  # fmt: skip


@dataclass
class Block:
    """Un bloque de Markdown ya clasificado. `kind`: heading | table | quote | item | para | pruebate."""

    kind: str
    text: str  # texto «plano»: items/párrafos unidos con espacio; quote con saltos de línea
    lines: list[str] = field(default_factory=list)  # líneas originales (sin `>` en quote)
    level: int = 0  # solo heading


@dataclass
class Table:
    header: list[str]
    rows: list[list[str]]


@dataclass
class Section:
    heading: str
    lines: list[str]


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Separa el frontmatter YAML del cuerpo. YAML inválido o no-dict → `{}` y el cuerpo sin él."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text.lstrip("﻿")
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        data = None
    return (data if isinstance(data, dict) else {}), text[m.end() :]


def frontmatter_tags(meta: dict) -> list[str]:
    """Tags del frontmatter como lista de str sin `#` (acepta lista o cadena separada por comas/espacios)."""
    raw = meta.get("tags", meta.get("tag"))
    if raw is None:
        return []
    items = re.split(r"[,\s]+", raw) if isinstance(raw, str) else [str(t) for t in raw if t is not None]
    return [t.strip().lstrip("#") for t in items if t and t.strip().lstrip("#")]


def clean_inline(text: str) -> str:
    """Quita imágenes, comentarios HTML y `<br>`; `[[ruta|alias]]` → alias; `[t](url)` → t."""
    text = _HTML_COMMENT_RE.sub("", text)
    text = _WIKI_EMBED_RE.sub("", text)
    text = _IMG_RE.sub("", text)
    text = _BR_RE.sub(" ", text)

    def wiki(m: re.Match[str]) -> str:
        alias = m.group(2)
        if alias is not None and alias.strip():
            return alias.strip()
        target = m.group(1).split("#")[0].strip()
        return target.rsplit("/", 1)[-1] if target else m.group(1).strip()

    text = _WIKI_RE.sub(wiki, text)
    text = _LINK_RE.sub(r"\1", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def strip_bold(text: str) -> str:
    return BOLD_RE.sub(r"\1", text)


def strip_code_blocks(text: str) -> str:
    """Elimina los bloques de código con valla (``` o ~~~), sin tocar el resto."""
    out: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        m = FENCE_RE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)[0]
                continue
            out.append(line)
        elif m and m.group(1)[0] == fence:
            fence = None
    return "\n".join(out)


def first_h1(body: str) -> str:
    for line in strip_code_blocks(body).splitlines():
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == 1:
            return strip_bold(clean_inline(m.group(2)))
    return ""


def _is_table_line(line: str) -> bool:
    return line.lstrip().startswith("|")


def _is_special(line: str) -> bool:
    return bool(
        HEADING_RE.match(line)
        or ITEM_RE.match(line)
        or line.lstrip().startswith(">")
        or _is_table_line(line)
        or HRULE_RE.match(line)
        or FENCE_RE.match(line)
        or PRUEBATE_RE.match(line)
        or _DEFLINE_RE.match(line)
    )


def iter_blocks(text: str) -> Iterator[Block]:
    """Recorre el cuerpo y emite bloques; los bloques de código se omiten por completo.

    Una línea «Pruébate» siempre es un bloque propio (kind `pruebate`, `text` = la pregunta).
    """
    lines = text.splitlines()
    i, n = 0, len(lines)
    fence: str | None = None
    while i < n:
        line = lines[i]
        m_fence = FENCE_RE.match(line)
        if fence is not None:
            if m_fence and m_fence.group(1)[0] == fence:
                fence = None
            i += 1
            continue
        if m_fence:
            fence = m_fence.group(1)[0]
            i += 1
            continue
        if not line.strip() or HRULE_RE.match(line):
            i += 1
            continue
        m = HEADING_RE.match(line)
        if m:
            yield Block("heading", strip_bold(clean_inline(m.group(2))), [line], level=len(m.group(1)))
            i += 1
            continue
        mp = PRUEBATE_RE.match(line)
        if mp:
            yield Block("pruebate", clean_inline(mp.group(1)), [line])
            i += 1
            continue
        if _is_table_line(line):
            start = i
            while i < n and _is_table_line(lines[i]):
                i += 1
            chunk = lines[start:i]
            yield Block("table", "\n".join(chunk), chunk)
            continue
        if line.lstrip().startswith(">"):
            start = i
            while i < n and lines[i].lstrip().startswith(">") and not PRUEBATE_RE.match(lines[i]):
                i += 1
            chunk = [re.sub(r"^\s*(?:>\s?)+", "", ln) for ln in lines[start:i]]
            if not chunk:  # la línea es un «> Pruébate:» ya tratado arriba; no debería ocurrir
                i += 1
                continue
            yield Block("quote", "\n".join(chunk), chunk)
            continue
        mi = ITEM_RE.match(line)
        if mi:
            chunk = [line]
            i += 1
            while i < n and lines[i].strip() and not _is_special(lines[i]):
                chunk.append(lines[i])
                i += 1
            joined = " ".join([mi.group(2).strip(), *[c.strip() for c in chunk[1:]]])
            yield Block("item", joined, chunk)
            continue
        start = i
        i += 1
        while i < n and lines[i].strip() and not _is_special(lines[i]):
            i += 1
        chunk = lines[start:i]
        yield Block("para", " ".join(c.strip() for c in chunk), chunk)


def split_row(line: str) -> list[str]:
    s = line.strip()
    s = s.removeprefix("|").removesuffix("|") if not s.endswith("\\|") else s.removeprefix("|")
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def parse_table(lines: list[str]) -> Table | None:
    """Tabla con cabecera + separador + filas. `None` si no tiene forma de tabla."""
    if len(lines) < 2 or not TABLE_SEP_RE.match(lines[1]) or "-" not in lines[1]:
        return None
    header = [clean_inline(c) for c in split_row(lines[0])]
    rows: list[list[str]] = []
    for ln in lines[2:]:
        cells = [clean_inline(c).replace("\\|", "|") for c in split_row(ln)]
        cells = (cells + [""] * len(header))[: len(header)]
        rows.append(cells)
    return Table(header, rows)


def split_sections(lines: list[str], level: int) -> list[Section]:
    """Divide en secciones por heading del nivel dado (los niveles más profundos quedan dentro)."""
    sections: list[Section] = []
    current: Section | None = None
    fence: str | None = None
    for line in lines:
        m_fence = FENCE_RE.match(line)
        if m_fence and (fence is None or m_fence.group(1)[0] == fence):
            fence = None if fence else m_fence.group(1)[0]
        m = HEADING_RE.match(line) if fence is None and not m_fence else None
        if m and len(m.group(1)) == level:
            current = Section(strip_bold(clean_inline(m.group(2))), [])
            sections.append(current)
        elif m and len(m.group(1)) < level:
            current = None
        elif current is not None:
            current.lines.append(line)
    return sections


def iter_entries(lines: list[str]) -> Iterator[tuple[str, str]]:
    """Entradas de una sección: bullets de primer nivel o `###`. Devuelve `(titulo_###_o_'', cuerpo)`.

    El cuerpo conserva el Markdown (con sangría de continuación quitada). El texto previo a la
    primera entrada se ignora, igual que los párrafos sueltos que siguen a un bullet tras línea en blanco.
    """
    title = ""
    buf: list[str] = []
    kind = ""  # "bullet" | "h3" | ""
    blank = False
    entries: list[tuple[str, str]] = []

    def flush() -> None:
        body = textwrap.dedent("\n".join(buf)).strip()
        if kind and body:
            entries.append((title, body))

    for line in lines:
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == 3:
            flush()
            title, buf, kind, blank = strip_bold(clean_inline(m.group(2))), [], "h3", False
        elif re.match(r"^[-*+]\s+", line):
            flush()
            title, buf, kind, blank = "", [re.sub(r"^[-*+]\s+", "", line)], "bullet", False
        elif not line.strip():
            blank = True
            if kind:
                buf.append("")
        elif kind and (kind == "h3" or not blank or line[:1] in " \t"):
            buf.append(line.removeprefix("  ") if kind == "bullet" else line)
            blank = False
        else:  # párrafo suelto fuera de una entrada
            flush()
            title, buf, kind, blank = "", [], "", False
    flush()
    yield from entries


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def is_trivial_term(term: str) -> bool:
    t = term.strip().rstrip(":").strip().lower()
    return t in LABEL_TERMS or not re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", t) or t.isdigit()


def cloze_pairs(text: str, *, max_cards: int) -> list[tuple[str, str, str]]:
    """Huecos de una oración por negrita: `(oración_original, front, término)`.

    Reglas: oración 40-300 chars, 1 o 2 negritas de 2-60 chars, sin etiquetas triviales
    (`**Nota**`), y que fuera de la negrita queden ≥ 25 chars (no es solo un titular en negrita).
    """
    out: list[tuple[str, str, str]] = []
    if max_cards <= 0:
        return out
    for sentence in split_sentences(re.sub(r"\s+", " ", clean_inline(text))):
        if not 40 <= len(sentence) <= 300 or "|" in sentence:
            continue
        bolds = list(BOLD_RE.finditer(sentence))
        if not 1 <= len(bolds) <= 2 or sentence.count("**") != 2 * len(bolds):
            continue
        for m in bolds:
            term = m.group(1).strip()
            if not 2 <= len(term) <= 60 or is_trivial_term(term) or term.endswith(":"):
                continue
            if sentence[m.end() : m.end() + 1] == ":" and m.start() == 0:  # «**Etiqueta**: …» no es un hueco
                continue
            front = sentence[: m.start()] + "**[…]**" + sentence[m.end() :]
            if len(strip_bold(sentence.replace(m.group(0), ""))) < 25 or front.lstrip("*[…] ").startswith(":"):
                continue
            out.append((sentence, front, term))
            if len(out) >= max_cards:
                return out
    return out
