import json

from app.importers.base import make_key
from app.importers.cmdvault import parse_cmdvault


def _cmd(title, command="ls -la", **extra):
    return {"title": title, "command": command, "section": "Sec", "topic": "Top", "description": "Hace algo.", **extra}


def _write(d, name, slug, cmds, cat_name="Cat"):
    data = {"category": {"slug": slug, "name": cat_name, "icon": "x", "order": 1}, "commands": cmds}
    (d / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_comando_completo(tmp_path):
    ex = [{"description": f"Ej {i}", "code": f"cmd {i}"} for i in range(3)]
    cmd = _cmd("Listar archivos", examples=ex, tags=["ls"], level="básico", roadmap=["devops"], extra="ignorado")
    _write(tmp_path, "a.json", "linux", [cmd], "Linux")
    drafts, rep = parse_cmdvault(tmp_path)
    assert rep.files_seen == 1 and rep.drafts == 1 and rep.errors == []
    d = drafts[0]
    assert (d.deck_slug, d.deck_name, d.deck_source, d.kind) == ("cmd-linux", "Comandos · Linux", "cmdvault", "comando")
    assert d.front == "**Listar archivos**\n\nHace algo.\n\n_Sec › Top_\n\n¿Qué comando lo hace?"
    assert d.back.startswith("```bash\nls -la\n```") and "- Ej 1" in d.back and "Ej 2" not in d.back
    assert d.tags == ("ls", "básico", "devops")
    assert d.key == make_key("cmdvault", "linux", "listar-archivos")
    assert d.context == "CmdVault › Linux › Sec › Top"


def test_lenguaje_y_varios_archivos_misma_categoria(tmp_path):
    _write(tmp_path, "a.json", "windows", [_cmd("Uno", "dir")])
    _write(tmp_path, "b.json", "windows", [_cmd("Dos", "cd"), _cmd("Dos", "cd otra vez")])
    _write(tmp_path, "c.json", "mysql", [_cmd("SQL", "SELECT 1;", examples=[{"code": "SELECT 2;"}])])
    _write(tmp_path, "d.json", "mongodb", [_cmd("Mongo", "db.a.find()")])
    drafts, rep = parse_cmdvault(tmp_path)
    assert len(drafts) == 4 and len({d.deck_slug for d in drafts}) == 3
    by = {d.front.split("**")[1]: d for d in drafts}
    assert by["Uno"].back.startswith("```powershell")
    assert by["SQL"].back.startswith("```sql") and "SELECT 2;" in by["SQL"].back
    assert by["Mongo"].back.startswith("```javascript")


def test_fence_con_backticks_en_el_codigo(tmp_path):
    _write(tmp_path, "a.json", "git", [_cmd("Cita", "echo '```'")])
    drafts, _ = parse_cmdvault(tmp_path)
    assert drafts[0].back.startswith("````bash")


def test_errores_y_secretos(tmp_path):
    (tmp_path / "roto.json").write_text("{no es json", encoding="utf-8")
    (tmp_path / "sin_categoria.json").write_text("{}", encoding="utf-8")
    _write(tmp_path, "b.json", "git", [_cmd(""), "texto", _cmd("Token", "export TOKEN=abcdef123456789"), _cmd("Ok")])
    drafts, rep = parse_cmdvault(tmp_path)
    assert [d.front.split("**")[1] for d in drafts] == ["Token", "Ok"]  # el seed no filtra secretos
    assert rep.skipped_secret == 0 and len(rep.errors) == 4 and rep.files_seen == 3


def test_directorio_inexistente(tmp_path):
    drafts, rep = parse_cmdvault(tmp_path / "no")
    assert drafts == [] and rep.errors
