# Tessera

**An open-source, MCP-native benchmark for whether AI agents reason reliably over fragmented enterprise knowledge.**

> *tessera* (n.): a single tile of a mosaic. No tile is the picture. The picture is how they fit.

[![status](https://img.shields.io/badge/status-pre--v0-orange)](#roadmap)
[![license](https://img.shields.io/badge/code-Apache--2.0-blue)](#license)
[![data](https://img.shields.io/badge/data-CC--BY--4.0-blue)](#license)

> ⚠️ **Building in public.** This is a manifesto and a spec in progress, not a finished benchmark. v0.1 is targeted for **mid-2026**. Follow along, open issues, tell me where I'm wrong.

---

## The problem

The bottleneck for enterprise AI agents is no longer generating code or prose. It's reasoning reliably over the knowledge a company actually has. That knowledge is scattered across wikis, CRMs, tickets, chat threads, and half-stale PDFs. It contradicts itself. It has gaps.

In that setting an agent has to do three hard things at once:

1. **Get the answer right** when the answer exists.
2. **Cite where it came from.** Provenance, not vibes.
3. **Refuse** when the data isn't there, instead of confidently making something up.

Today's agent benchmarks mostly measure tool-use mechanics or single-source QA. Almost nothing measures reliability over fragmented, contradictory enterprise knowledge. "Looks right in the demo, fails silently in production" is exactly the gap that keeps agents out of serious work.

Tessera is a way to measure that gap.

## What Tessera measures

Every task is scored on three axes, not one:

| Axis | Question | Why it matters |
|---|---|---|
| **Accuracy** | Did the agent reach the correct answer? | Table stakes, but not enough on its own. |
| **Provenance** | Did it cite the right source(s) for that answer? | A right answer from the wrong or guessed source is a lucky guess, not reliability. |
| **Correct refusal** | When the knowledge is absent or contradictory, did it say "I don't know" or surface the conflict, instead of hallucinating? | The most under-measured agent behavior, and the one enterprises care about most. |

A model that scores high on accuracy but low on refusal is dangerous, not good. Tessera is designed to make that visible.

## Why MCP-native

Tessera exposes the synthetic "company" to the agent through the [Model Context Protocol](https://modelcontextprotocol.io), the same way a real enterprise agent reaches a CRM, a docs store, or a ticketing system. That means:

- The benchmark tests the agent the way it would actually be deployed, over MCP tools, not through a bespoke harness.
- Any MCP-compatible agent or model can be evaluated with no Tessera-specific glue.
- The retrieval surface (search, fetch, list) is realistic: noisy, paginated, partial.

## What Tessera is *not*

- ❌ Not a coding benchmark, and not a general agent-capability leaderboard.
- ❌ Not a RAG accuracy test on a clean single corpus.
- ❌ Not built on real company data. The public dataset is synthetic by design (see [Integrity](#integrity--limitations)).
- ❌ Not a vibes eval. Every metric is defined, scriptable, and reproducible.

## How it works (v0 design)

```
┌─────────────────────┐     MCP      ┌──────────────────┐
│  Synthetic org       │  <───────>  │  Agent under test │
│  (fragmented, noisy, │   tools:    │  (any MCP client) │
│   contradictory)     │  search /   └──────────────────┘
│                      │  fetch /            │
│  • docs / wiki        │  list              ▼
│  • CRM-like records   │            ┌──────────────────┐
│  • chat threads       │            │  Scorer           │
│  • tickets / emails   │            │  accuracy +       │
└─────────────────────┘            │  provenance +     │
            ▲                        │  correct-refusal  │
            │ generator              └──────────────────┘
   seeds + controllable
   fragmentation / conflict
```

1. **Dataset generator.** Produces a synthetic organization with controllable fragmentation: facts split across sources, deliberate contradictions, and deliberate gaps. Difficulty is a knob, not an accident.
2. **MCP harness.** Serves that org over MCP tools to the agent under test.
3. **Task suites.** Questions whose ground truth includes the answer, the supporting source(s), and whether a faithful agent should refuse.
4. **Scorer.** Computes the three metrics and emits a per-task trace you can audit.

## Quickstart

> Coming with v0.1. The intended shape:

```bash
# (placeholder, not yet released)
pip install tessera-bench
tessera run --agent my-mcp-agent --suite core-v0
tessera report
```

Watch [Releases](../../releases) or star the repo to know when it's real.

## Roadmap

- [ ] **v0.1 (mid-2026).** Dataset generator, MCP harness, one core task suite, the three metrics, a README you can actually run.
- [ ] Public leaderboard with frontier models.
- [ ] Companion write-up (arXiv) on measuring enterprise-agent reliability.
- [ ] Additional suites: cross-source synthesis, temporal staleness, conflicting-policy resolution.
- [ ] Community-contributed task suites.

## Integrity & limitations

Honesty is what makes a benchmark citable, so this section matters as much as the rest.

- **Synthetic, public, reproducible.** No real client data ever enters the public dataset. Real-world data is used only as private validation that the synthetic distribution is realistic.
- **Documented bias.** The generator encodes assumptions about how organizations fragment knowledge. Those assumptions will be wrong in places, and they'll be written down so results can be read in context.
- **Gameable if leaked.** Like any benchmark, a memorized test set is meaningless. Held-out suites and rotating seeds are part of the design.
- **A measure, not the territory.** A high Tessera score is evidence of reliability under these conditions. It is not a guarantee in yours.

## Related work

Tessera builds on and differs from agent and tool benchmarks such as the **τ-bench** family and other tool-use and reliability evaluations. The difference: Tessera's unit of difficulty is fragmentation and contradiction across enterprise knowledge, and it treats provenance and correct refusal as first-class scored axes, not afterthoughts. The full related-work section lives in the companion paper.

## Contributing

Early, opinionated, and open. The most useful contributions right now:

- Failure cases: an enterprise reasoning task where good agents should refuse but don't.
- Critiques of the metric definitions, especially provenance scoring.
- Realistic fragmentation patterns the generator should model.

Open an issue before a large PR. See `CONTRIBUTING.md` (coming with v0.1).

## About

Built by **Rinaldo Festa**. I build and measure the reliability layer for enterprise AI agents (MCP, memory, provenance), in the open.
Research log and context: **[rinaldofesta.com](https://rinaldofesta.com)**.

## License

- **Code:** Apache-2.0
- **Synthetic dataset:** CC-BY-4.0

*(To confirm before the first release. These are the recommended defaults for an open, citable benchmark.)*
