# Extending Tessera: adding a silo type

Silos are pluggable. A silo type bundles: an MCP server module (run via
`python -m`, reads `TESSERA_OUT` for the compiled org), its tool names, a
prompt blurb, a consulted-claims credit function, and (optionally) custom
compile build/write hooks.

```python
from tessera.silos.registry import SiloType

LAKE = SiloType(
    name="lake",
    server_module="tessera_lake.mcp.catalog_server",
    tool_names=("search_datasets", "get_dataset_metadata", "query_series", "list_tags"),
    prompt_blurb=" You can also query a data-lake catalog (search_datasets, "
                 "get_dataset_metadata, query_series, list_tags).",
    consulted=lake_consulted,   # (tool_name, args, result, manifest) -> set[claim_id]
    build=lake_build,           # (claims) -> (payload, manifest_entries)   [optional]
    write=lake_write,           # (payload, out_dir) -> None                [optional]
)
```

Publish it from your package via the entry-point group:

```toml
[project.entry-points."tessera.silo_types"]
lake = "your_pack.silo:LAKE"
```

Tessera discovers it lazily on first registry lookup. An entry point may also
load to an iterable of `SiloType`s, or a zero-arg callable returning either, which
is useful when one pack registers several silo types. A broken entry point is
skipped with a logged warning rather than breaking the registry. Claims with
`silo="lake"` then compile through your build/write hooks (or the default
field/prose renderer if you don't define them), the eval task launches your
MCP server alongside the built-ins, and scoring credits consulted claims
through your `consulted` function.
