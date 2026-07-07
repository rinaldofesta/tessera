# Architecture Decision Records

Short, immutable records of the decisions that shaped Tessera — one decision per file,
numbered in the order they were accepted. A record is never edited after acceptance;
if a decision is reversed, a new ADR supersedes it and the old one's status says so.

The cadence: each working week closes with the ADRs for the decisions it made.

| # | Date | Title | Status |
|---|------|-------|--------|
| [0001](0001-k-lives-in-the-task.md) | 2026-06-11 | The epoch count and the pass^k reducer live together in the task | Accepted |
| [0002](0002-response-models-are-the-contract.md) | 2026-06-11 | Pydantic response models are the API contract | Accepted |
| [0003](0003-score-the-committed-answer.md) | 2026-06-11 | The deterministic engine scores the committed answer | Accepted |
| [0004](0004-retire-the-streamlit-ui.md) | 2026-06-11 | Retire the legacy Streamlit UI | Accepted |
| [0005](0005-per-field-crm-provenance.md) | 2026-06-11 | Per-field CRM provenance: credit what the agent actually received | Accepted |
| [0006](0006-meridian-and-the-leaderboard-protocol.md) | 2026-06-11 | Meridian ships as the public reference org; the leaderboard protocol | Accepted |
| [0007](0007-delegation-mvp.md) | 2026-06-12 | Reliability under delegation: a two-stage chain, not handoff() | Accepted |
| [0008](0008-scenario-factory-and-holdout-protocol.md) | 2026-06-19 | The scenario-factory and the holdout protocol | Accepted |
| [0009](0009-refusal-aware-scaffold-intervention.md) | 2026-06-28 | The refusal-aware scaffold intervention | Accepted |
| [0010](0010-the-leaderboard-is-generated-from-a-manifest.md) | 2026-07-07 | The leaderboard is generated from a committed manifest | Accepted |
| [0011](0011-harness-is-a-displayed-comparability-axis.md) | 2026-07-07 | Harness is a displayed comparability axis, not a guarded one | Accepted |
| [0012](0012-leaderboard-rows-are-verified-against-committed-logs.md) | 2026-07-07 | Leaderboard rows are verified against committed logs | Accepted |
