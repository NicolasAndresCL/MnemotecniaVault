from pathlib import Path

from app.importers.base import make_key
from app.importers.proyectos import parse_projects

APR = """# Aprendizaje — Demo

Intro ignorada.

## FastAPI / uvicorn

- **El `lifespan` corre una vez POR WORKER.** Con dos workers el arranque se ejecuta en paralelo.
  Arreglo: un lock de base de datos al inicio.
- sin negrita pero con un texto largo que supera las doce palabras para recortar el gancho del todo

## Postgres

### Cambió la ruta del volumen

La imagen nueva guarda los datos en otra carpeta, así que el volumen debe montarse en `/var/lib/postgresql`.

## Vacía
"""


def _proj(root: Path, name: str, text: str | None) -> None:
    d = root / name
    d.mkdir(parents=True)
    if text is not None:
        (d / "aprendizaje.md").write_text(text, encoding="utf-8")


def test_lecciones_y_cloze(tmp_path):
    _proj(tmp_path, "Mi Proyecto", APR)
    drafts, rep = parse_projects(tmp_path)
    assert rep.files_seen == 1 and rep.drafts == len(drafts) and rep.errors == []
    lec = [d for d in drafts if d.kind == "leccion"]
    assert len(lec) == 3
    a, b, c = lec
    assert (a.deck_slug, a.deck_name, a.deck_source) == ("lecciones-mi-proyecto", "Lecciones · Mi Proyecto", "proyecto")
    assert (
        a.front
        == "**FastAPI / uvicorn** · ¿qué trampa o lección hay detrás de: «El `lifespan` corre una vez POR WORKER»?"
    )
    assert "Arreglo: un lock" in a.back
    assert a.context == "Mi Proyecto/aprendizaje.md › FastAPI / uvicorn"
    assert a.tags == ("fastapi-uvicorn", "mi-proyecto")
    assert a.key == make_key("proyecto", "Mi Proyecto", "FastAPI / uvicorn", "El `lifespan` corre una vez POR WORKER")
    assert b.front.endswith("sin negrita pero con un texto largo que supera las doce palabras…»?")
    assert "«Cambió la ruta del volumen»" in c.front and c.back.startswith("La imagen nueva")
    assert all(d.kind in ("leccion", "cloze") for d in drafts)


def test_cloze_con_tope_y_recorte(tmp_path):
    frases = " ".join(f"La herramienta **pieza{i}** resulta indispensable para el flujo completo." for i in range(20))
    _proj(tmp_path, "P", f"## T\n\n- {frases}\n- {'x' * 3000}\n")
    drafts, _ = parse_projects(tmp_path)
    assert sum(d.kind == "cloze" for d in drafts) == 10
    assert max(len(d.back) for d in drafts if d.kind == "leccion") <= 1500


def test_saltos_secretos_y_duplicados(tmp_path):
    _proj(tmp_path, "env", APR)
    _proj(tmp_path, "node_modules", APR)
    _proj(tmp_path, "sin_archivo", None)
    _proj(
        tmp_path,
        "Secreto",
        "## T\n\n- **Clave filtrada** password = abcdef123456 en el texto.\n- **Dup** uno\n- **Dup** dos\n",
    )
    (tmp_path / "suelto.txt").write_text("x", encoding="utf-8")
    drafts, rep = parse_projects(tmp_path)
    assert rep.files_seen == 1 and rep.skipped_secret == 2  # la lección y su cloze
    dup = [d for d in drafts if "Dup" in d.front]
    assert len(dup) == 2 and dup[0].key != dup[1].key


def test_error_de_lectura_y_raiz_inexistente(tmp_path, monkeypatch):
    _proj(tmp_path, "P", APR)

    def boom(self, *a, **k):
        raise OSError("boom")

    monkeypatch.setattr(Path, "read_text", boom)
    drafts, rep = parse_projects(tmp_path)
    assert drafts == [] and "boom" in rep.errors[0]
    drafts, rep = parse_projects(tmp_path / "no")
    assert drafts == [] and rep.errors
