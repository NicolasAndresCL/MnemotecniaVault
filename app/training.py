"""Gimnasio de memoria: ejercicios adaptativos de memoria de trabajo (lógica pura).

- **Dígitos** (span de dígitos): repetir una tira de cifras que crece al acertar. Medida clásica de
  memoria de trabajo; con *chunking* y sistema mayor se supera el «7 ± 2».
- **Sistema mayor**: traducir número ↔ palabra hasta que el código sea automático.
- **Pares asociados**: memorizar pares palabra–palabra y recuperar uno dado el otro (se entrena la
  asociación con imagen, base de todos los ganchos).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.mnemonics import LEXICON, word_to_digits

GAMES: dict[str, tuple[str, str, str]] = {
    "digitos": ("Span de dígitos", "pin", "Repite la tira de cifras. Agrúpalas de a 3 o conviértelas en palabras."),
    "sistema_mayor": ("Sistema mayor", "tag", "Convierte el número en una palabra (o la palabra en número)."),
    "pares": ("Pares asociados", "link", "Une cada par con una imagen absurda; luego recupera la pareja."),
}


@dataclass
class Level:
    """Nivel adaptativo tipo escalera: sube al acertar, baja tras dos fallos seguidos."""

    value: int = 4
    minimum: int = 2
    maximum: int = 40
    fails: int = 0
    best: int = 0
    history: list[bool] = field(default_factory=list)

    def record(self, ok: bool) -> None:
        self.history.append(ok)
        if ok:
            self.best = max(self.best, self.value)
            self.value = min(self.maximum, self.value + 1)
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= 2:
            self.value = max(self.minimum, self.value - 1)
            self.fails = 0


def digit_sequence(length: int, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    return "".join(str(rng.randint(0, 9)) for _ in range(length))


def check_digits(expected: str, typed: str) -> bool:
    return "".join(ch for ch in typed if ch.isdigit()) == expected


def major_challenge(rng: random.Random | None = None) -> tuple[str, str]:
    """Devuelve (número de 2 cifras, palabra del léxico que lo codifica) para un reto."""
    rng = rng or random.Random()
    candidates = [w for w in LEXICON if len(word_to_digits(w)) == 2]
    word = rng.choice(candidates)
    return word_to_digits(word), word


def check_major_word(number: str, typed_word: str) -> bool:
    """Cualquier palabra vale si su código fonético es exactamente el número."""
    return bool(typed_word.strip()) and word_to_digits(typed_word) == number


def word_pairs(n: int, rng: random.Random | None = None) -> list[tuple[str, str]]:
    rng = rng or random.Random()
    words = rng.sample(sorted(set(LEXICON)), n * 2)
    return [(words[i], words[i + n]) for i in range(n)]


def score_pairs(pairs: list[tuple[str, str]], answers: dict[str, str]) -> int:
    return sum(1 for a, b in pairs if answers.get(a, "").strip().lower() == b.lower())
