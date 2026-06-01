# Tessera

**An open methodology and generator for building your own reliability eval for AI agents, over your own fragmented knowledge, reached via MCP.**

> *tessera* (n.): a single tile of a mosaic. No tile is the picture. The picture is how they fit.

[![status](https://img.shields.io/badge/status-pre--v0-orange)](#status-and-roadmap)
[![license](https://img.shields.io/badge/code-Apache--2.0-blue)](#license)
[![data](https://img.shields.io/badge/data-CC--BY--4.0-blue)](#license)

> ⚠️ **Building in public.** Methodology and generator in progress. v0 targeted **mid-2026**. No models measured yet, and I will not pretend otherwise until they are. Open issues, tell me where I am wrong.

---

## The problem

Models can already do almost anything. The open problem is doing it reliably. The bottleneck for enterprise AI agents is not generating code or prose, it is reasoning over the knowledge a company actually has: scattered across wikis, CRMs, tickets, chat threads, and half-stale PDFs, contradictory, and full of gaps.

In that setting an agent has to do three hard things at once:

1. **Get the answer right** when the answer exists.
2. **Cite where it came from.** Provenance, not vibes.
3. **Refuse** when the data is missing or the sources conflict, instead of confidently making something up.

Public agent benchmarks mostly measure tool-use mechanics or single-source QA. They are a model's SAT score: a wide number, not the signal you need. The signal you need is your own interview, on your own data.

## What Tessera is, and is not

Tessera is **not another public leaderboard.** It is a **methodology and a reproducible generator** (the `tessera-scenario-factory`). Point it at a company's fragmented, contradictory, siloed knowledge, reached only over MCP the way a real agent would, and it builds **that company's own reliability eval**.

The public dataset and leaderboard are a **showcase, not the product.** The eval you build on your own data is the point. A public benchmark is the SAT score. Your own eval is the interview.

## What it measures

Every task is scored on more than accuracy, and repeated because models are stochastic:

- **Cross-source retrieval over MCP**, because one source is never the whole picture.
- **Multi-turn memory and consistency**, because agents forget mid-conversation.
- **Accuracy with provenance**, because an answer you cannot trace is an answer you cannot trust.
- **Correct refusal**, because the strongest signal is a clean "I do not know" when the sources conflict or the data is missing.
- **pass^k**, because a stochastic model has to be tested more than once.

## How it works (v0 design)

```
generator ──> synthetic fragmented org ──MCP──> agent under test ──> scorer
(controllable    docs / CRM / tickets / PDFs,                         accuracy +
 fragmentation   siloed, contradictory                               provenance +
 and conflict)                                                       correct refusal,
                                                                     repeated pass^k
```

1. **Generator** produces a synthetic organization with controllable fragmentation: facts split across sources, deliberate contradictions, deliberate gaps. Difficulty is a knob, not an accident. Synthetic by design, so no real company data is ever exposed.
2. **MCP harness** serves that org to the agent under test over MCP tools, the same surface it would use in production.
3. **Task suites** require cross-source reasoning, memory, and the judgment to refuse.
4. **Scorer** computes accuracy, provenance, and correct refusal, repeated with pass^k, and emits a per-task trace you can audit.

## The pairing

A factory is a deterministic algorithm that orchestrates stochastic agents to build the same on-spec system every time. Build factories, not features.

**A factory is how you build the system. Tessera is how you verify it is reliable.**

## Why this is white space

No open benchmark sits at the intersection of OSS, enterprise fragmentation, MCP-native access, provenance, correct refusal, and a generator you point at your own data:

- **τ-bench / τ²-bench** measure tool-use and policy on a single, clean database, not multi-source fragmentation.
- **ReliabilityBench** measures generic consistency and fault tolerance, not fragmented enterprise knowledge.
- **GBA-Bench** has enterprise context and memory but is proprietary and closed.

Related work is consolidated in the companion thesis.

## Status and roadmap

- [ ] **v0 (mid-2026)** generator, MCP harness, one core task suite, the scorer, a runnable quickstart.
- [ ] Showcase: a public synthetic dataset and a leaderboard of frontier models run against it.
- [ ] Companion write-up on measuring enterprise-agent reliability.
- [ ] `tessera-scenario-factory`: point it at your own knowledge and generate your own eval.

No models have been measured yet. When they are, the numbers go here.

## Integrity and limitations

Honesty is what makes an eval citable.

- **Synthetic, public, reproducible.** No real client data ever enters the public dataset. Real data stays a private validation testbed.
- **Documented bias.** The generator encodes assumptions about how organizations fragment knowledge. Those assumptions will be wrong in places, and they will be written down.
- **A measure, not the territory.** A score is evidence under these conditions, not a guarantee in yours.

## Contributing

Early and open. The most useful contributions now: a real enterprise reasoning task where good agents should refuse but do not, critiques of the metric definitions (especially provenance and refusal scoring), and realistic fragmentation patterns the generator should model. Open an issue before a large PR.

## About

Built by **Rinaldo Festa**. I build AI agents for enterprises, then I build the evals that prove they can be trusted. Context and the build log: **[rinaldofesta.com](https://rinaldofesta.com)**.

## Run the toy eval (v0 preview)

> Requires a model API key (e.g. `ANTHROPIC_API_KEY`).

```bash
uv pip install -e .
.venv/bin/inspect eval src/tessera/evals/task.py --model anthropic/claude-sonnet-4-6 --display plain
.venv/bin/inspect view   # open the log: per-sample tool calls, provenance, refusal
```

The toy organization has two MCP silos (a structured CRM and an unstructured Docs
store) and three probes — a cross-source lookup, a resolvable contradiction, and a
question with no answer in the data. Each is scored on accuracy, **provenance**
(which sources the agent actually consulted, read from its real tool calls), and
**correct refusal**, repeated under `pass_k` epochs. Accuracy and refusal are
deterministic in v0; model-graded scoring (and an independent grader bound via
`--model-role grader=<other-model>`) is a planned upgrade.

## License

- **Code:** Apache-2.0
- **Synthetic dataset:** CC-BY-4.0
