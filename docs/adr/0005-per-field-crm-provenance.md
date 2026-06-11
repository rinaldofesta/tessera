# ADR-0005 — Per-field CRM provenance: credit what the agent actually received

- **Date**: 2026-06-11
- **Status**: Proposed (design for Week 3; implementation would ship as `det-4`)

## Context

Provenance credit is computed mechanically from the agent's recorded tool *calls*
mapped through the compiled manifest (`consulted_claims`, `scoring.py`). For docs
this is naturally claim-granular — one `.md` file per prose claim, credited by
`artifact` path. For the CRM it collapses to **subject-granular**: one
`crm_lookup("Acme Corp")` credits *every* CRM claim for that subject, because the
tool returns the whole record and the call arguments carry no field signal.

Two facts make this fixable cheaply:

1. **The manifest is already field-addressed.** Every CRM entry carries
   `predicate` and a `locator` of the form `"Acme Corp.renewal_date"` — unused by
   the scorer today.
2. **The tool response's top-level keys *are* the manifest predicates.** The
   compiled `db.json` maps `subject → {predicate → {value, asserted_at}}`, so
   field-level attribution is a dict-key intersection, no new compiler output.

There is also a latent honesty bug worth fixing on the way: credit is granted from
the *call*, so a `crm_lookup` that returned `NOT_FOUND` or errored still counts as
"consulted."

## Decision (proposed)

A hybrid of response-shape attribution with a field-filtering tool parameter:

1. **`crm_lookup(account_name, fields=None)`** — the tool gains an optional list of
   field names; the silo layer filters the returned record to those predicates.
   The task prompt teaches the parameter (otherwise agents never exercise it and
   the metric silently stays subject-granular).
2. **The scorer credits the *response*, not the request.** Pair each assistant
   `ToolCall` with its `ChatMessageTool` result via `tool_call_id` (both already
   in `state.messages`; today the tool messages are discarded), parse the
   `crm_lookup` JSON, and credit the CRM manifest entries whose `subject` matches
   the call and whose `predicate` is a key of the *returned* record.
   - `NOT_FOUND` / errored / unparseable responses credit nothing — fixing the
     latent over-credit.
   - An unfiltered lookup still returns (and credits) the whole record: existing
     blueprints score identically until agents start using `fields`, so the
     tightening is observable, not a silent cliff.
3. **`scorer_version` bumps to `det-4`** (and the llm engine, which shares the
   deterministic provenance signal, to `llm-2`); trend comparisons partition on
   it — provenance rates can only drop across this boundary, so an unpartitioned
   trend line would read as a regression.

## Alternatives considered

- **Credit follows the request** (`fields` param alone): fully mechanical but
  measures *intent*, not access — the agent is credited for fields it requested
  even if the lookup failed. Weakest evidence; rejected as the credit basis,
  retained as the filtering mechanism.
- **Field-addressed tool surface** (`crm_get_field(account, field)`, one call =
  one locator): the purest credit semantics, but it changes the *world* to make
  measurement easy — a one-field-per-call CRM is less representative of real
  systems than a filterable lookup, every existing blueprint silently gets harder,
  and agent behavior/cost changes for reasons unrelated to reliability. Rejected.

## Consequences

- Provenance stays **fully mechanical** — JSON parsing of recorded messages, zero
  model judgment — and becomes *stronger*: credit now means the field's data
  demonstrably reached the agent's context.
- New coupling: the scorer depends on the `crm_lookup` response format. Needs a
  loud failure mode if inspect_ai ever truncates or restructures tool content in
  the log (content can be a `Content` list, not a raw string).
- Old logs keep rendering (the report layer reads stored `consulted` metadata
  verbatim and never re-scores); pinned example reports stay truthful as
  historical artifacts marked by their `scorer_version`.
- Blueprint schema untouched: `expected_sources` remain claim_ids, and a claim_id
  already denotes exactly one field.
