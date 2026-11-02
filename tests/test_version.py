"""La versión dice lo mismo en todos los lugares donde vive (skill `release-y-tag`, §2).

Lugares: `pyproject.toml`, `app/__init__.py` (`__version__`, lo expone `/api/health`), README (badge, tabla
Versión/Fecha y pie), `k8s/kustomization.yaml` (`newTag`) y la primera sección versionada del CHANGELOG.
Así un desfase se ve en el PR y no recién cuando `release.yml` rechaza el tag.

Refactor: Nicolás Cano Leal
Fecha: 2026-11-02
"""

import re
import tomllib
from pathlib import Path

from app import __version__

RAIZ = Path(__file__).resolve().parents[1]


def _leer(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8")


VERSION = tomllib.loads(_leer("pyproject.toml"))["project"]["version"]


def test_version_es_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+(-rc\.\d+)?", VERSION)


def test_paquete_y_pyproject_coinciden():
    assert __version__ == VERSION


def test_changelog_tiene_la_version_como_ultima_publicada():
    changelog = _leer("CHANGELOG.md")
    assert "## [Sin publicar]" in changelog
    ultima = re.search(r"^## \[(\d+\.\d+\.\d+[^\]]*)\] — \d{4}-\d{2}-\d{2}$", changelog, re.M)
    assert ultima and ultima.group(1) == VERSION


def test_readme_badge_tabla_y_pie():
    readme = _leer("README.md")
    assert f"versi%C3%B3n-{VERSION.replace('-', '--')}-blue" in readme
    assert f"| **Versión** | {VERSION} |" in readme
    assert re.search(rf"^Mnemotecnia Vault v{re.escape(VERSION)} · .+$", readme, re.M)


def test_imagen_de_kubernetes():
    assert f'newTag: "{VERSION}"' in _leer("k8s/kustomization.yaml")
