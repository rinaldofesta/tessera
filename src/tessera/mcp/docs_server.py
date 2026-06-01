"""Docs silo MCP server (stdio). Reads the compiled org at $TESSERA_OUT."""

from __future__ import annotations

import json
import os

from mcp.server.fastmcp import FastMCP

from tessera.silos.access import docs_get_file as _get_file
from tessera.silos.access import docs_search as _search

_OUT = os.environ.get("TESSERA_OUT", ".")
mcp = FastMCP("tessera-docs")


@mcp.tool()
def docs_search(query: str) -> str:
    """Search the document store; returns a JSON list of {path, excerpt}."""
    return json.dumps(_search(_OUT, query))


@mcp.tool()
def docs_get_file(path: str) -> str:
    """Return the full text of a document by its path (e.g. 'docs/x.md')."""
    return _get_file(_OUT, path)


if __name__ == "__main__":
    mcp.run()  # stdio transport (default)
