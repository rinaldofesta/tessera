import re
from pathlib import Path

from tessera import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_single_across_package_metadata():
    pyproject = (ROOT / "pyproject.toml").read_text()
    citation = (ROOT / "CITATION.cff").read_text()
    project_version = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    citation_version = re.search(r'^version: "([^"]+)"$', citation, re.MULTILINE)
    assert project_version and citation_version
    assert project_version.group(1) == citation_version.group(1) == __version__ == "0.2.0"
