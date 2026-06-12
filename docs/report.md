# Tessera: a deterministic benchmark for enterprise agent reliability

**Rinaldo Festa** · June 12, 2026 · scorer `det-4` · results as of 2026-06-12
Repository: <https://github.com/rinaldofesta/tessera> · Protocol: [ADR-0006](adr/0006-meridian-and-the-leaderboard-protocol.md)

## Abstract

*(written last — Task 10)*

## 1. Introduction

Enterprise knowledge does not live in one place. It fragments across a CRM, a documentation wiki, a renewal tracker, ticket queues — and the fragments disagree. A system of record and a departmental tracker carry different values for the same contract field, with timestamps and authority that give neither precedence. An agent asked a question over this substrate must do more than retrieve: it must reconcile silos, and when the evidence is symmetric — when no honest reading of the sources yields a winner — the reliable behavior is to refuse and escalate, not to produce a confident answer. Fabricating a tie-break is the failure mode that matters in production, because it is the one that looks like success.

Capability is not reliability. A model that answers correctly 2 times in 3 is a demo, not a system: deployed unwatched, it is wrong on a schedule. The metric has to encode this, so Tessera's headline is strict pass^k — a probe counts only if every one of its k repetitions passes. Mean accuracy is reported alongside, as capability when the dice land well; it is never the headline.

What gets graded is equally deliberate. Tessera scores what the agent commits to: its final `ANSWER:` line, not the reasoning above it. The canonical enterprise failure is helpful-sounding analysis — the conflict noticed, the sources weighed, the hedge articulated — followed by a fabricated commitment. An agent that reasons correctly and then commits to an invented value has failed in exactly the way a downstream consumer of the answer cannot detect, so the committed line decides both accuracy and refusal.

One scope statement bounds every claim in this report: Tessera scores policy *execution*, not policy *discovery*. The agent is told the reconciliation policy — a source that declares itself binding wins even over a fresher one; absent declared authority, the most recent wins; refuse where neither rule disambiguates or the record is absent. The question measured is not whether an agent can infer a sensible policy on its own, but whether it executes a stated one reliably, repetition after repetition. Discovery is a separate and harder problem; conflating the two would make results on either uninterpretable.

The thesis of this report is that the instrument is the contribution, and the measurements are the evidence that the instrument works. Concretely, we contribute:

- **An open benchmark generator.** A Blueprint — declarative claims plus probes — is compiled deterministically into a fragmented synthetic organization, served to the agent under test over two MCP servers: the same access surface a production agent would use, with the fragmentation and the contradictions placed by design rather than by accident.
- **A deterministic scorer of the committed answer**, on three axes: accuracy against the committed line, per-field provenance read from the agent's real MCP traffic, and committed refusal. The scorer is versioned (`det-4`), so every published result names the exact rules that produced it.
- **A frozen comparability protocol**: strict pass^k with k owned by the task definition rather than the runner, executable comparability guards that abort non-comparable configurations instead of warning about them, and transcript adjudication of every probe that fails all k repetitions — so a consistent failure is diagnosed, not merely counted.
- **Two measured findings.** First, no evaluated model reliably refuses the symmetric tie: the leaderboard's unresolvable column reads 40/0/0/0/0 at k=3, and the dominant failure is a fabricated tie-break committed as fact. Second, a delegation hop is a faithful conduit: it laundered every upstream fabrication into downstream settled fact (3/3 relayed) while never destroying a correct refusal (0/12). The hop inherits the decision; it does not audit it.

The remainder of the report presents related work, the method and protocol, the experiments behind both findings, and the limitations that bound what these measurements license.

## 2. Related work

## 3. Method

### 3.1 Blueprint: claims, probes, and a conflict taxonomy

### 3.2 Deterministic compilation into a fragmented environment

### 3.3 Scoring the committed answer (`det-4`)

### 3.4 The comparability protocol

## 4. Experiment 1: a five-model leaderboard

## 5. Experiment 2: reliability under delegation

## 6. Limitations

## 7. Future work

## References
