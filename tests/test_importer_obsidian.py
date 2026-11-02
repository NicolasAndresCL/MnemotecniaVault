from pathlib import Path

from app.importers.base import make_key
from app.importers.obsidian import parse_vault


def _w(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


DEF = "- **Término**: una definición suficientemente larga para ser válida.\n"

NOTA = """---
tags: [demo]
---
# Nota de prueba

> **Resumen:** una nota sintética que explica
> el funcionamiento de la caché local.

## Conceptos

- **Caché**: almacén temporal de datos usados con frecuencia para acelerar lecturas.
- **Nota**: corta.
**Latencia** — tiempo que tarda una petición en recibir su respuesta completa.
- **Versión**: 1.2.3

La **idempotencia** garantiza que repetir una operación no cambia el resultado final obtenido.

| Capa | Rol | Puerto |
|---|---|---|
| Web | Sirve la interfaz | 8080 |
| API | Expone datos | 8000 |
| Vacía |  | 1 |
| Solo uno | Algo | |

| X | Y |
|---|---|
| 1 | 2 |

## Ficha

Un gancho para recordar el orden de los pasos.
**Pruébate:** ¿cuál es el orden de los pasos?

```
**Código**: no debe generar nada porque está dentro de un bloque de código.
```
"""


def test_genera_todos_los_tipos(tmp_path):
    _w(tmp_path, "01 Proyectos/Demo/nota.md", NOTA)
    drafts, rep = parse_vault(tmp_path)
    kinds = {d.kind for d in drafts}
    assert kinds == {"definicion", "tabla", "pruebate", "resumen", "cloze"}
    assert rep.files_seen == 1 and rep.drafts == len(drafts) and rep.errors == []
    assert {d.deck_slug for d in drafts} == {"obsidian-demo"} and drafts[0].deck_name == "Demo"
    assert drafts[0].deck_source == "obsidian" and "proyectos" in drafts[0].tags and "demo" in drafts[0].tags

    por = {k: [d for d in drafts if d.kind == k] for k in kinds}
    assert {d.front for d in por["definicion"]} == {"¿Qué es **Caché**?", "¿Qué es **Latencia**?"}
    cache = next(d for d in por["definicion"] if "Caché" in d.front)
    assert cache.back.startswith("almacén temporal") and cache.context == "01 Proyectos/Demo/nota.md › Conceptos"
    # La tabla X/Y (1 → 2) es numérica y la de 3 columnas tiene solo 2 filas válidas.
    assert [d.front for d in por["tabla"]] == [
        "**Capa: Web** → ¿Rol?",
        "**Capa: API** → ¿Rol?",
        "**Capa: Solo uno** → ¿Rol?",
    ]
    assert por["tabla"][0].back == "Sirve la interfaz\n\n- **Puerto**: 8080"
    assert por["pruebate"][0].front == "¿cuál es el orden de los pasos?"
    assert por["pruebate"][0].back == "Un gancho para recordar el orden de los pasos."
    assert por["resumen"][0].front == "Resume con tus palabras la nota «Nota de prueba»"
    assert por["resumen"][0].back == "una nota sintética que explica el funcionamiento de la caché local."
    assert [(d.front.count("[…]"), d.back) for d in por["cloze"]] == [(1, "idempotencia")]
    assert all("Código" not in d.front + d.back for d in drafts)
    assert len({(d.deck_slug, d.key) for d in drafts}) == len(drafts)


def test_mazos_segun_ruta(tmp_path):
    for rel in ["suelta.md", "00 Inbox/idea.md", "02 Áreas/Salud/dieta.md", "Libre/otra.md", "Libre/sub/x.md"]:
        _w(tmp_path, rel, DEF)
    drafts, _ = parse_vault(tmp_path)
    decks = {d.deck_name: d.deck_slug for d in drafts}
    assert decks == {
        "Vault": "obsidian-vault",
        "Inbox": "obsidian-inbox",
        "Salud": "obsidian-salud",
        "Libre": "obsidian-libre",
        "sub": "obsidian-sub",
    }
    assert next(d for d in drafts if d.deck_name == "Inbox").tags == ("inbox",)


def test_saltos(tmp_path):
    for rel in [
        "_sistema/a.md",
        ".obsidian/b.md",
        ".trash/c.md",
        "x_files/d.md",
        "01 Proyectos/P/aprendizaje.md",
        "01 Proyectos/P/MEMORY.md",
        "01 Proyectos/P/pendientes.md",
        "01 Proyectos/P/CHANGELOG.md",
        "01 Proyectos/P/CLAUDE.md",
        "01 Proyectos/P/nota.txt",
    ]:
        _w(tmp_path, rel, DEF)
    _w(tmp_path, "01 Proyectos/P/idx1.md", "---\ntags: [indice-generado]\n---\n" + DEF)
    _w(tmp_path, "01 Proyectos/P/idx2.md", "#indice-generado\n" + DEF)
    _w(tmp_path, "01 Proyectos/P/grande.md", DEF + "x" * (401 * 1024))
    _w(tmp_path, "01 Proyectos/P/buena.md", DEF)
    drafts, rep = parse_vault(tmp_path)
    assert [d.context for d in drafts] == ["01 Proyectos/P/buena.md"]
    assert rep.files_seen == 9


def test_secretos_bytes_invalidos_y_keys_duplicadas(tmp_path):
    _w(
        tmp_path,
        "01 Proyectos/P/n.md",
        "- **Clave**: password = abcdef123456 es la contraseña para el servidor interno.\n"
        "- **Repetido**: primera definición que es suficientemente larga para pasar.\n"
        "- **Repetido**: segunda definición que es suficientemente larga para pasar.\n",
    )
    raro = b"- **Raro**: definici\xf3n con bytes inv\xe1lidos pero larga igual.\n"
    (tmp_path / "01 Proyectos/P/malo.md").write_bytes(raro)
    drafts, rep = parse_vault(tmp_path)
    assert rep.skipped_secret == 1 and rep.errors == []
    reps = [d for d in drafts if "Repetido" in d.front]
    assert len(reps) == 2 and reps[0].key != reps[1].key
    assert reps[0].key == make_key("obsidian", "01 Proyectos/P/n.md", "definicion", "", "Repetido")
    assert any("Raro" in d.front for d in drafts)


def test_error_de_lectura_no_lanza(tmp_path, monkeypatch):
    _w(tmp_path, "a.md", DEF)

    def boom(self, *a, **k):
        raise PermissionError("denegado")

    monkeypatch.setattr(Path, "read_text", boom)
    drafts, rep = parse_vault(tmp_path)
    assert drafts == [] and len(rep.errors) == 1 and "denegado" in rep.errors[0]


def test_raiz_inexistente(tmp_path):
    drafts, rep = parse_vault(tmp_path / "nada")
    assert drafts == [] and rep.errors


def test_archivo_y_tablas_tecnicas_y_max_tablas(tmp_path):
    _w(tmp_path, "04 Archivo/Viejo/n.md", DEF)
    _w(tmp_path, "01 Proyectos/04 Archivo/n.md", DEF)
    tec = "| K | V |\n|---|---|\n| `src/app.py` | ruta |\n| mi_var | snake |\n| MiClase | camel |\n"
    tec += "| f() | llamada |\n| doc.md | md |\n| Dos palabras | valido |\n"
    tabla = "| A | B |\n|---|---|\n| uno | aaa |\n| dos | bbb |\n\n"
    _w(tmp_path, "01 Proyectos/P/t.md", tec + "\n" + tabla * 4)
    drafts, _ = parse_vault(tmp_path)
    assert not any(d.context.startswith("04 Archivo") for d in drafts)
    assert any(d.context.startswith("01 Proyectos/04 Archivo") for d in drafts)
    tablas = [d for d in drafts if d.kind == "tabla"]
    assert len(tablas) == 1 + 2 + 2  # "Dos palabras" + dos tablas simples (máximo 3 tablas por nota)


def test_limites_tabla_y_cloze(tmp_path):
    filas = "\n".join(f"| clave{i} | valor número {i} |" for i in range(40))
    sin_cabecera = "|  | b |\n|---|---|\n| x | y |\n| z | w |\n"
    una_fila = "| a | b |\n|---|---|\n| xx | yy |\n"
    siete = (
        "| a | b | c | d | e | f | g |\n|---|---|---|---|---|---|---|\n"
        + "| uno | dos | tres | cuatro | cinco | seis | siete |\n" * 2
    )
    frases = "\n\n".join(
        f"La función **concepto{i}** resulta fundamental para entender el sistema completo." for i in range(30)
    )
    _w(tmp_path, "n.md", f"| K | V |\n|---|---|\n{filas}\n\n{sin_cabecera}\n{una_fila}\n{siete}\n{frases}\n")
    drafts, _ = parse_vault(tmp_path)
    assert sum(d.kind == "tabla" for d in drafts) == 12
    assert sum(d.kind == "cloze" for d in drafts) == 15
