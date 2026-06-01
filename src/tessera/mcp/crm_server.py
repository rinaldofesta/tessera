"""CRM silo MCP server (stdio). Reads the compiled org at $TESSERA_OUT."""

from __future__ import annotations

import json
import os

from mcp.server.fastmcp import FastMCP

from tessera.silos.access import crm_lookup_record

_OUT = os.environ.get("TESSERA_OUT", ".")
mcp = FastMCP("tessera-crm")


@mcp.tool()
def crm_lookup(account_name: str) -> str:
    """Look up a CRM account by exact name; returns its fields as JSON, or 'NOT_FOUND'."""
    record = crm_lookup_record(_OUT, account_name)
    return json.dumps(record) if record is not None else "NOT_FOUND"


if __name__ == "__main__":
    mcp.run()  # stdio transport (default)
