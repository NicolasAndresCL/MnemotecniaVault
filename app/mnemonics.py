"""Generadores de técnicas mnemotécnicas (funciones puras, sin BD ni UI).

Ninguna técnica reemplaza el recuerdo activo: dan el «asa» para tirar del dato; después hay que
recuperarlo sin mirar y repasarlo a intervalos crecientes (eso lo hace `app.srs`).
"""

from __future__ import annotations

import random
import re
import unicodedata

from app.models import TECHNIQUES

# --------------------------------------------------------------------------- sistema mayor
# Código fonético: cada cifra es un SONIDO consonante; vocales, H, W e Y vocal no cuentan.
# Adaptado al español: B y V suenan igual, así que ambas son 9; C/G cambian según la vocal siguiente.
MAJOR_TABLE: list[tuple[int, str, str]] = [
    (0, "S, Z, C (ce, ci)", "La S de «cero» empieza con sonido de S"),
    (1, "T, D", "La T tiene un solo palo vertical"),
    (2, "N, Ñ", "La N tiene dos patas"),
    (3, "M", "La M tiene tres patas"),
    (4, "R, RR", "«cuatRo» termina en R"),
    (5, "L", "La mano abierta: cinco dedos, el pulgar y el índice forman una L"),
    (6, "CH, J, G (ge, gi), LL, Y consonante", "La J reflejada parece un 6"),
    (7, "K, Q, C (ca, co, cu), G (ga, go, gu)", "La K se arma con dos sietes"),
    (8, "F", "La f manuscrita tiene dos bucles, como el 8"),
    (9, "P, B, V", "La P es un 9 reflejado"),
]

LEXICON = [
    "oso",
    "sol",
    "sal",
    "suela",
    "taza",
    "tos",
    "té",
    "tía",
    "dado",
    "diente",
    "nido",
    "nube",
    "mano",
    "mono",
    "mapa",
    "mesa",
    "mar",
    "rana",
    "ratón",
    "rosa",
    "rey",
    "rueda",
    "luna",
    "lana",
    "lobo",
    "lápiz",
    "llave",
    "lluvia",
    "chile",
    "jarra",
    "jamón",
    "gema",
    "gel",
    "yoyo",
    "kiwi",
    "queso",
    "casa",
    "cama",
    "copa",
    "cubo",
    "gato",
    "gol",
    "gorro",
    "foca",
    "faro",
    "fuego",
    "fideo",
    "pato",
    "pan",
    "pino",
    "palo",
    "piña",
    "pez",
    "bota",
    "vaso",
    "vela",
    "baño",
    "bote",
    "boca",
    "barco",
    "bala",
    "balón",
    "dedo",
    "dama",
    "duna",
    "dino",
    "techo",
    "taco",
    "tubo",
    "tren",
    "trigo",
    "tambor",
    "tomate",
    "televisor",
    "zapato",
    "silla",
    "sopa",
    "saco",
    "sapo",
    "sirena",
    "nariz",
    "nieve",
    "nota",
    "nuez",
    "mono",
    "mito",
    "muela",
    "mula",
    "mochila",
    "momia",
    "mesa",
    "rata",
    "red",
    "ropa",
    "rubí",
    "rata",
    "lata",
    "loro",
    "leche",
    "lima",
    "limón",
    "libro",
    "llama",
    "chancho",
    "jabón",
    "jefe",
    "jirafa",
    "yate",
    "queque",
    "cohete",
    "cuna",
    "cola",
    "coco",
    "cuchillo",
    "gallo",
    "guante",
    "goma",
    "fresa",
    "foto",
    "fósforo",
    "flecha",
    "pera",
    "pelota",
    "piano",
    "pipa",
    "pulpo",
    "búho",
    "bolso",
    "bombo",
    "vaca",
    "vino",
    "violín",
    "vela",
    "cerdo",
    "cine",
    "cisne",
    "cebolla",
    "cereza",
    "ojo",
    "hielo",
    "uña",
    "ola",
    "hoja",
    "oreja",
    "uva",
    "humo",
    "aguja",
    "anillo",
    "abeja",
    "araña",
    "ancla",
]


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def word_to_digits(word: str) -> str:
    """Traduce una palabra (o frase) a cifras según el sistema mayor en español."""
    w = word.lower().replace("ñ", "\x00")  # la Ñ no debe perderse al quitar tildes
    w = _strip_accents(w).replace("\x00", "ñ")
    w = re.sub(r"[^a-zñ]", "", w)
    digits: list[str] = []
    i = 0
    while i < len(w):
        c, nxt = w[i], w[i + 1 : i + 2]
        pair = w[i : i + 2]
        if pair in ("ch", "ll"):
            digits.append("6")
            i += 2
            continue
        if pair == "rr":
            digits.append("4")
            i += 2
            continue
        if pair == "qu" or (c == "g" and nxt == "u" and w[i + 2 : i + 3] in ("e", "i")):
            digits.append("7")
            i += 2
            continue
        if c == "c":
            digits.append("0" if nxt in ("e", "i") else "7")
        elif c == "g":
            digits.append("6" if nxt in ("e", "i") else "7")
        elif c == "y":
            # Y consonante solo si va antes de vocal («yate»); al final o entre consonantes suena vocal.
            if nxt in ("a", "e", "i", "o", "u"):
                digits.append("6")
        elif c == "x":
            digits.extend(("7", "0"))  # «ks»
        else:
            code = {
                "s": "0", "z": "0", "t": "1", "d": "1", "n": "2", "ñ": "2", "m": "3", "r": "4",
                "l": "5", "j": "6", "k": "7", "q": "7", "f": "8", "p": "9", "b": "9", "v": "9",
            }.get(c)  # fmt: skip
            if code:
                digits.append(code)
        i += 1
    return "".join(digits)


def peg_words(number: str, lexicon: tuple[str, ...] | list[str] = tuple(LEXICON)) -> dict[str, list[str]]:
    """Sugiere palabras del léxico para cada trozo de 2 cifras (o 1 si sobra) del número."""
    clean = re.sub(r"\D", "", number)
    by_code: dict[str, list[str]] = {}
    for word in dict.fromkeys(lexicon):
        by_code.setdefault(word_to_digits(word), []).append(word)
    chunks = [clean[i : i + 2] for i in range(0, len(clean), 2)]
    return {ch: by_code.get(ch, []) for ch in chunks}


# --------------------------------------------------------------------------- acrónimos
VIVID_WORDS: dict[str, list[str]] = {
    "a": ["Abuela", "Avestruz", "Astronauta"], "b": ["Ballena", "Bombero", "Bruja"], "c": ["Camello", "Cohete"],
    "d": ["Dragón", "Dinosaurio"], "e": ["Elefante", "Enano"], "f": ["Flamenco", "Fantasma"], "g": ["Gorila", "Gigante"],
    "h": ["Hipopótamo", "Hada"], "i": ["Iguana", "Iceberg"], "j": ["Jirafa", "Jaguar"], "k": ["Koala", "Karateca"],
    "l": ["León", "Llama"], "m": ["Mono", "Momia"], "n": ["Ninja", "Nutria"], "o": ["Oso", "Ogro"],
    "p": ["Pingüino", "Pirata"], "q": ["Quesero", "Quetzal"], "r": ["Robot", "Rinoceronte"], "s": ["Sirena", "Samurái"],
    "t": ["Tiburón", "Titán"], "u": ["Unicornio", "Uróboros"], "v": ["Vampiro", "Vikingo"], "w": ["Wookiee"],
    "x": ["Xilófono"], "y": ["Yeti", "Yak"], "z": ["Zorro", "Zombi"],
}  # fmt: skip
VERBS = ["baila", "come", "pinta", "lanza", "abraza", "persigue", "cocina", "despega"]


def initials(items: list[str]) -> str:
    """Iniciales en mayúscula de cada elemento: la base de un acrónimo."""
    out = []
    for it in items:
        m = re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", it)
        if m:
            out.append(_strip_accents(m.group(0)).upper() if m.group(0).lower() != "ñ" else "Ñ")
    return "".join(out)


def acronym_phrase(items: list[str], seed: int | None = None) -> str:
    """Frase absurda cuyas palabras empiezan con las iniciales (el acróstico es más fácil de evocar)."""
    rng = random.Random(seed)
    words = []
    for idx, letter in enumerate(initials(items).lower()):
        pool = VIVID_WORDS.get(letter, [letter.upper() + "…"])
        word = rng.choice(pool)
        words.append(word if idx == 0 else word.lower())
        if idx == 0 and len(items) > 2:
            words.append(rng.choice(VERBS))
    return " ".join(words)


# --------------------------------------------------------------------------- texto
def first_letters(text: str) -> str:
    """Técnica de las primeras letras: deja la inicial y la puntuación (memorizar textos literales)."""
    return re.sub(r"([A-Za-zÁÉÍÓÚÑáéíóúñü])[A-Za-zÁÉÍÓÚÑáéíóúñü]*", r"\1", text)


def chunk_digits(number: str, size: int = 3) -> str:
    """Chunking: agrupa una tira de cifras (la memoria de trabajo sostiene ~4 trozos, no 12 cifras)."""
    clean = re.sub(r"\D", "", number)
    return " ".join(clean[i : i + size] for i in range(0, len(clean), size))


def cloze(text: str, term: str) -> str:
    """Oculta `term` en `text` (sin distinguir mayúsculas)."""
    return re.sub(re.escape(term), "[…]", text, flags=re.IGNORECASE)


def normalize_answer(text: str) -> str:
    plain = _strip_accents(re.sub(r"[`*_>#\[\]()]", " ", text or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ ]", " ", plain)).strip()


def answer_similarity(typed: str, expected: str) -> float:
    """Parecido 0–1 entre lo escrito y la respuesta (palabras clave compartidas). Solo orienta: califica uno."""
    a, b = set(normalize_answer(typed).split()), set(normalize_answer(expected).split())
    b -= {"el", "la", "los", "las", "de", "del", "y", "o", "a", "en", "un", "una", "que", "con", "por", "para"}
    if not b:
        return 1.0 if a else 0.0
    return round(len(a & b) / len(b), 2)


# --------------------------------------------------------------------------- plantillas de gancho
TEMPLATES: dict[str, str] = {
    "acronimo": "Iniciales: {initials}\nFrase: {phrase}",
    "frase_ancla": "«{short}» → regla en imperativo, corta, que se pueda decir en voz alta.",
    "rima": "Rima de dos versos que termine en el término exacto: «… {short}».",
    "imagen_absurda": "Escena exagerada, en movimiento y con un sentido (olor, ruido) que represente «{short}».",
    "contraste_espejo": "«X con X, Y con Y»: une cada término con su par por una letra o sonido compartido.",
    "asociacion_forma": "¿A qué se parece el símbolo? Forma → significado.",
    "palacio": "Estación del palacio + escena: coloca «{short}» en un lugar de tu casa.",
    "sistema_mayor": "Cifras {digits} → palabras {pegs}",
    "historia": "Une los pasos en una historia donde cada uno provoca el siguiente.",
}


def _list_items(back: str) -> list[str]:
    items = re.findall(r"^\s*(?:[-*]|\d+[.)])\s+(.+)$", back, flags=re.MULTILINE)
    if not items:
        items = [p.strip() for p in re.split(r"[,;·]| y ", back) if p.strip()]
    return items[:12]


def suggest_hook(technique: str, front: str, back: str, seed: int | None = None) -> str:
    """Borrador de gancho para que el usuario lo personalice (los ganchos propios recuerdan mejor)."""
    if technique not in TECHNIQUES:
        raise ValueError(f"Técnica desconocida: {technique}")
    short = re.sub(r"\s+", " ", re.sub(r"[`*_#>]", "", back)).strip()[:60]
    items = _list_items(back)
    digits = re.sub(r"\D", "", back)[:8]
    pegs = " · ".join(f"{k}={'/'.join(v[:2]) or '?'}" for k, v in peg_words(digits).items()) if digits else "—"
    return TEMPLATES[technique].format(
        initials=initials(items) or "—",
        phrase=acronym_phrase(items, seed) if items else "—",
        short=short,
        digits=digits or "—",
        pegs=pegs,
    )


def recommend_technique(kind: str, back: str) -> str:
    """Qué técnica conviene según el tipo de dato (tabla de la skill `mnemotecnia`)."""
    if re.search(r"\d{2,}", back):
        return "sistema_mayor"
    if len(_list_items(back)) >= 3 and re.search(r"^\s*(?:[-*]|\d+[.)])\s", back, flags=re.MULTILINE):
        return "historia" if re.search(r"^\s*\d+[.)]", back, flags=re.MULTILINE) else "acronimo"
    if kind == "comando":
        return "imagen_absurda"
    if kind == "leccion":
        return "frase_ancla"
    if kind in ("definicion", "cloze") and len(back) < 80:
        return "rima"
    return "imagen_absurda"


DEFAULT_PALACE_STATIONS = [
    "Puerta de entrada",
    "Recibidor",
    "Living",
    "Comedor",
    "Cocina",
    "Pasillo",
    "Baño",
    "Dormitorio",
    "Escritorio (el setup)",
    "Ventana",
    "Patio",
]
