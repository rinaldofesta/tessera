"""Packaged, terminal-friendly guidance for first-time Tessera users."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import tessera
from tessera.errors import SpecError

_TOPICS = ("start", "conflicts", "suites", "reading", "agents")


def _topic_text(name: str) -> str:
    resource = resources.files("tessera.data").joinpath("guide", f"{name}.md")
    return resource.read_text(encoding="utf-8")


def _agents_text() -> str:
    checkout = Path(tessera.__file__).parents[2] / "AGENTS.md"
    if checkout.is_file():
        return checkout.read_text(encoding="utf-8")
    packaged = resources.files("tessera.data").joinpath("guide", "AGENTS.md")
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    raise SpecError("the coding-agent guide is missing")


def _source_text(name: str) -> str:
    """The one place that decides where a topic's text comes from — shared by
    `_metadata()` and `text()` so `guide --list`'s summary is always drawn from the
    exact same document `guide TOPIC` prints (previously `_metadata("agents")` read a
    separately-maintained packaged copy while `text("agents")` preferred the checkout
    root AGENTS.md, so the two could silently disagree)."""
    return _agents_text() if name == "agents" else _topic_text(name)


def _metadata(name: str) -> dict[str, str]:
    lines = _source_text(name).splitlines()
    title = next(line[2:].strip() for line in lines if line.startswith("# "))
    heading_index = next(index for index, line in enumerate(lines) if line.startswith("# "))
    paragraph: list[str] = []
    for line in lines[heading_index + 1:]:
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith("#"):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    return {"name": name, "title": title, "summary": " ".join(paragraph)}


def topics() -> list[dict[str, str]]:
    """Return stable topic metadata in the order used by the CLI."""
    return [_metadata(name) for name in _TOPICS]


def text(name: str) -> str:
    """Load one topic, with the agent guide resolved for source and wheel layouts."""
    if name not in _TOPICS:
        raise SpecError(f"unknown guide topic '{name}'; available: {', '.join(_TOPICS)}")
    return _source_text(name)
