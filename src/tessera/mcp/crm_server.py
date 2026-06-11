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
    record = crm_lookup_record(_OUT, account_name)
    if record is None:
        return "NOT_FOUND"
    if fields is None:
        return json.dumps(record)
    known = {k: v for k, v in record.items() if k in set(fields)}
    unknown = [f for f in fields if f not in record]
    if unknown:  # name the miss — '{}' must not be ambiguous with "field is empty"
        return json.dumps({**known, "_unknown_fields": unknown,
                           "_available_fields": sorted(record)})
    return json.dumps(known)


if __name__ == "__main__":
    mcp.run()  # stdio transport (default)
