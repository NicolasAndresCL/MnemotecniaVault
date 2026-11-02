from app.importers import markdown as md


def test_frontmatter_ok_invalid_and_absent():
    meta, body = md.split_frontmatter("---\ntags: [a, b]\ntitle: T\n---\n# Hola\n")
    assert meta == {"tags": ["a", "b"], "title": "T"} and body.startswith("# Hola")
    assert md.split_frontmatter("---\n: : [\n---\ncuerpo")[0] == {}
    assert md.split_frontmatter("---\n- lista\n---\ncuerpo")[0] == {}
    assert md.split_frontmatter("sin frontmatter") == ({}, "sin frontmatter")


def test_frontmatter_tags_variantes():
    assert md.frontmatter_tags({"tags": ["#a", "b"]}) == ["a", "b"]
    assert md.frontmatter_tags({"tags": "a, #b c"}) == ["a", "b", "c"]
    assert md.frontmatter_tags({}) == []


def test_clean_inline():
    assert md.clean_inline("ver [[ruta/nota|alias]] y [[otra/nota#sec]] y [[solo]]") == "ver alias y nota y solo"
    assert md.clean_inline("![[foto.png]] texto ![alt](x.png) [link](http://x) <!-- c --> a<br>b") == "texto link a b"
    assert md.clean_inline("[[|]]") == ""
    assert md.strip_bold("**a** y **b**") == "a y b"


def test_strip_code_y_h1():
    text = "# Título **uno**\n```py\n# no\n```\ntexto\n~~~\n# no2\n~~~\n"
    assert md.strip_code_blocks(text) == "# Título **uno**\ntexto"
    assert md.first_h1(text) == "Título uno"
    assert md.first_h1("sin heading") == ""


def test_iter_blocks_clasifica():
    text = (
        "# H\n\npárrafo uno\nsigue\n\n- item **a**: algo\n  continúa\n- otro\n\n> cita\n> más\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n\n---\n```\ncodigo\n```\n**Pruébate:** ¿qué pasa?\n> Pruébate: ¿y ahora?\n"
        "- [ ] tarea\n"
    )
    blocks = list(md.iter_blocks(text))
    kinds = [b.kind for b in blocks]
    assert kinds == ["heading", "para", "item", "item", "quote", "table", "pruebate", "pruebate", "item"]
    assert blocks[1].text == "párrafo uno sigue"
    assert blocks[2].text == "item **a**: algo continúa"
    assert blocks[4].text == "cita\nmás"
    assert blocks[6].text == "¿qué pasa?" and blocks[7].text == "¿y ahora?"
    assert blocks[8].text == "tarea"


def test_parse_table():
    t = md.parse_table(["| A | B |", "|---|:--:|", "| x \\| y | `z` |", "| solo |"])
    assert t is not None
    assert t.header == ["A", "B"]
    assert t.rows == [["x | y", "`z`"], ["solo", ""]]
    assert md.parse_table(["| A |", "| no sep |"]) is None
    assert md.parse_table(["| A |"]) is None


def test_split_sections_y_entries():
    lines = (
        "intro\n## Uno\n- **Trampa A**: causa\n  más detalle\n\n- B simple\n\npárrafo suelto\n"
        "## Dos\n### Título H3\ncuerpo h3\n\nsegundo párrafo\n```\n## no es heading\n```\n# Raíz\ncola"
    ).splitlines()
    secs = md.split_sections(lines, 2)
    assert [s.heading for s in secs] == ["Uno", "Dos"]
    assert list(md.iter_entries(secs[0].lines)) == [("", "**Trampa A**: causa\nmás detalle"), ("", "B simple")]
    assert list(md.iter_entries(secs[1].lines)) == [
        ("Título H3", "cuerpo h3\n\nsegundo párrafo\n```\n## no es heading\n```")
    ]


def test_cloze_pairs_reglas():
    ok = "Django usa **LocMemCache** por defecto cuando no defines CACHES en la configuración."
    pairs = md.cloze_pairs(ok, max_cards=5)
    assert pairs == [(ok, ok.replace("**LocMemCache**", "**[…]**"), "LocMemCache")]
    assert md.cloze_pairs(ok, max_cards=0) == []
    dos = ok + " Además **gunicorn** reparte el trabajo entre procesos distintos."
    assert len(md.cloze_pairs(dos, max_cards=1)) == 1
    largo = " en una frase que es suficientemente larga de verdad."
    sin_cloze = [
        "**Nota**: esto es una frase suficientemente larga para pasar el filtro de largo.",
        "Corta con **negrita**.",
        "Una **a1** y **b2** y **c3**" + largo,
        "**Esto es todo un titular en negrita sin nada afuera aquí.**",
        "**Etiqueta**: la explicación continúa con bastante texto después de los dos puntos.",
        "Una celda | con **pipe** que nunca debe producir cloze aunque sea larga de sobra.",
    ]
    for texto in sin_cloze:
        assert md.cloze_pairs(texto, max_cards=5) == [], texto
    assert md.is_trivial_term("Ojo") and md.is_trivial_term("123") and not md.is_trivial_term("Redis")
