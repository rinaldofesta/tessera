"""Silo type registry: the plugin surface for tessera silos.

A SiloType bundles everything tessera core needs to know about one kind of
silo: how it is served over MCP, which tools it exposes, how tool calls map
back to consulted claims, and (optionally) how its claims compile to disk.
Built-in types (crm, docs) register on import of ``tessera.silos``;
third-party packs register via the ``tessera.silo_types`` entry-point group.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ENTRY_POINT_GROUP = "tessera.silo_types"

# (tool_name, tool_args, tool_result, manifest) -> claim_ids credited as consulted
ConsultedFn = Callable[[str, dict[str, Any], Any, dict[str, dict[str, Any]]], set[str]]
# (claims of this silo) -> (opaque artifacts payload, manifest entries keyed by claim_id)
BuildFn = Callable[[list[Any]], tuple[Any, dict[str, dict[str, Any]]]]
# (opaque artifacts payload, out_dir) -> writes files under out_dir
WriteFn = Callable[[Any, Path], None]


class UnknownSiloTypeError(KeyError):
    """A blueprint references a silo name no registered SiloType provides."""


@dataclass(frozen=True)
class SiloType:
    name: str
    server_module: str  # importable module serving this silo over stdio MCP (python -m ...)
    tool_names: tuple[str, ...]  # MCP tool names the server exposes
    prompt_blurb: str  # how the eval system prompt describes this silo
    consulted: ConsultedFn
    build: BuildFn | None = None  # None: compiler's default field/prose rendering
    write: WriteFn | None = None

    def __post_init__(self) -> None:
        if (self.build is None) != (self.write is None):
            raise ValueError("silo type must define both build and write, or neither")


class SiloRegistry:
    def __init__(self) -> None:
        self._types: dict[str, SiloType] = {}

    def register(self, silo_type: SiloType) -> None:
        if silo_type.name in self._types:
            raise ValueError(f"silo type {silo_type.name!r} already registered")
        for tool in silo_type.tool_names:
            owner = self.tool_owner(tool)
            if owner is not None:
                raise ValueError(
                    f"tool {tool!r} already provided by silo type {owner.name!r}"
                )
        self._types[silo_type.name] = silo_type

    def get(self, name: str) -> SiloType:
        try:
            return self._types[name]
        except KeyError:
            registered = ", ".join(sorted(self._types)) or "none"
            raise UnknownSiloTypeError(
                f"no silo type {name!r} registered (registered: {registered})"
            ) from None

    def get_optional(self, name: str) -> SiloType | None:
        return self._types.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(self._types)

    def tool_owner(self, tool_name: str) -> SiloType | None:
        for st in self._types.values():
            if tool_name in st.tool_names:
                return st
        return None


registry = SiloRegistry()
