"""CRM silo MCP server (stdio). Reads the compiled org at $TESSERA_OUT."""

from __future__ import annotations

import json
import os

from mcp.server.fastmcp import FastMCP

from tessera.silos.access import crm_lookup_record

_OUT = os.environ.get("TESSERA_OUT", ".")
mcp = FastMCP("tessera-crm")


@mcp.tool()
def crm_lookup(account_name: str, fields: list[str] | None = None) -> str:
    """Look up a CRM account by exact name; returns its fields as JSON, or 'NOT_FOUND'.

    Pass `fields` to fetch only the named fields — request just what you need. If a
    requested field name does not exist, the response lists it under
    '_unknown_fields' together with the record's '_available_fields', so a wrong
    guess is recoverable."""
    record = crm_lookup_record(_OUT, account_name, fields=fields)
    if record is None:
        return "NOT_FOUND"
    return json.dumps(record)


if __name__ == "__main__":
    mcp.run()  # stdio transport (default)
