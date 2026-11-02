"""Contrato común de los importadores: borradores puros, sin base de datos.

Cada importador recorre una fuente (vault de Obsidian, seed de CmdVault, proyectos) y devuelve
`CardDraft`. El runner (`app.importers.runner`) los persiste con upsert por `(deck_slug, key)`:
si el contenido cambia se actualiza el texto pero se conserva el progreso FSRS.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

# Tipos de tarjeta. Determinan cómo se muestran y qué modo de práctica se sugiere.
KINDS = (
    "definicion",  # término → definición
    "cloze",  # frase con un hueco ([…]) → término exacto
    "tabla",  # fila de una tabla: clave → valor
    "pruebate",  # pregunta «Pruébate» de un material mnemotécnico
    "resumen",  # nota destilada → su resumen (elaboración / Feynman)
    "comando",  # descripción → comando de terminal (CmdVault)
    "leccion",  # lección aprendida de aprendizaje.md
    "manual",  # creada a mano en la app
)

# Patrones que nunca deben entrar como contenido de una tarjeta (defensa en profundidad:
# el vault ya filtra secretos, pero una nota copiada podría traer uno).
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|password|passwd|secret|contraseña)\s*[:=]\s*\S{6,}"
    r"|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|xox[bpa]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}"
)


@dataclass(frozen=True)
class CardDraft:
    deck_slug: str
    deck_name: str
    deck_source: str  # "obsidian" | "cmdvault" | "proyecto"
    key: str  # identificador estable dentro del mazo (ver make_key)
    kind: str
    front: str  # Markdown
    back: str  # Markdown
    context: str = ""  # de dónde salió: "01 Proyectos/CmdVault/README.md › Arquitectura"
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class ImportReport:
    source: str
    files_seen: int = 0
    drafts: int = 0
    skipped_secret: int = 0
    errors: list[str] = field(default_factory=list)


def slugify(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-") or "sin-nombre"


def make_key(*parts: str) -> str:
    """Clave estable: depende del origen (ruta, sección, término), no del texto de la respuesta.

    Así, corregir la definición en la nota actualiza la tarjeta en vez de crear otra.
    """
    raw = "\x1f".join(p.strip().lower() for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def has_secret(*texts: str) -> bool:
    return any(SECRET_RE.search(t or "") for t in texts)
