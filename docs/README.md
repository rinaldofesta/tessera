# Tessera documentation

Start with the field guide, then go as deep as the question needs.

| document | what it answers |
|---|---|
| [`reading-the-scorecard.md`](reading-the-scorecard.md) | How to read a report: pass^k against mean, the four conflict kinds, the three axes, the receipt. |
| [`report.md`](report.md) | The technical report: method, limits, measured results. |
| [`leaderboard.md`](leaderboard.md) | The public table on meridian, rendered from [`leaderboard.rows.json`](leaderboard.rows.json). CI fails on drift. |
| [`scaffold.md`](scaffold.md) | The refusal-aware scaffold intervention (ADR-0009): design, paired McNemar, findings. |
| [`delegation.md`](delegation.md) | Reliability under delegation (ADR-0007): producer researches, consumer commits. |
| [`validation.md`](validation.md), [`validation-preregistration.md`](validation-preregistration.md) | The synthetic-to-real transfer question and the pre-registered study that will answer it. |
| [`roadmap.md`](roadmap.md) | What shipped, in order, with evidence, and what is next. |
| [`related-work.md`](related-work.md) | Where Tessera sits among the MCP benchmarks. |
| [`extending-silos.md`](extending-silos.md) | Adding a silo type from your own package through the entry-point group. |
| [`adr/`](adr/) | Fourteen decisions on record, one file each. |
| [`tessera-lesson.html`](tessera-lesson.html) | The interactive lesson the app serves at `/learn`. |

The same material, shorter, is inside the CLI: `tessera guide` lists five topics. Coding agents get the operating contract in [`../AGENTS.md`](../AGENTS.md) and the skills under [`../skills/`](../skills/).
