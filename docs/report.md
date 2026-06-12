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

Tessera inherits from six families of prior work; we take each in turn, closing with what it leaves unmeasured.

**Tool-use reliability.** [τ-bench](https://arxiv.org/abs/2406.12045) evaluates an agent operating domain API tools under policy documents while conversing with an LM-simulated user, judged by end-of-conversation database state. It is the origin of pass^k — all k i.i.d. trials of a task must succeed — the metric Tessera adopts as its headline. [τ²-bench](https://arxiv.org/abs/2506.07982) adds dual-control environments in which agent and simulated user both wield tools, and a compositional task generator — a genuine precursor of Tessera's generator, though it composes tasks within fixed hand-built domains. [BFCL](https://proceedings.mlr.press/v267/patil25a.html) checks function-call structure by AST matching at scale and does score abstention when no provided function applies, but reports single-run accuracy with no multi-trial metric. This family pioneered pass^k and task generation; none of it scores per-field provenance against actual tool returns, or refusal when two systems of record disagree with symmetric authority — the measurements Tessera makes central.

**General agent benchmarks.** [AgentBench](https://arxiv.org/abs/2308.03688) measures multi-turn decision-making across eight interactive environments; [GAIA](https://arxiv.org/abs/2311.12983) poses 466 real-world general-assistant questions requiring browsing and tool use, scored against unique ground truth; [WebArena](https://arxiv.org/abs/2307.13854) scores end-to-end functional success on 812 long-horizon tasks in a self-hosted web environment. All three are fixed datasets in which every task has a unique resolvable answer or end state, scored in a single run. They map what agents can do; Tessera asks whether a narrow set of enterprise behaviors holds up under repetition, provenance checking, and deliberately unresolvable conflicts — cases these designs exclude by construction.

**Agent safety and risk.** [ToolEmu](https://arxiv.org/abs/2309.15817) emulates tool execution with an LM and quantifies harmful-side-effect risk with an LM judge across 36 high-stakes toolkits; [AgentHarm](https://arxiv.org/abs/2410.09024) measures whether agents refuse explicitly malicious multi-step tasks — and, like Tessera, is distributed on [inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai). This family scores safety refusal: declining to do harm. Tessera scores epistemic refusal — committed abstention when symmetric evidence makes any answer a fabrication — with a deterministic versioned scorer over real MCP-served environments rather than LM emulation and LM judging.

**Enterprise and work-domain agents.** [CRMArena](https://arxiv.org/abs/2411.02305) places agents in a synthesized Salesforce-style org of sixteen interconnected object types; [CRMArena-Pro](https://arxiv.org/abs/2505.18878) extends it across sales, service, and CPQ, and adds a confidentiality-awareness assessment — a refusal measurement, though its target is data leakage, not evidence. [WorkBench](https://arxiv.org/abs/2405.00823) scores 690 workplace tasks deterministically against a unique correct final database state; [TheAgentCompany](https://arxiv.org/abs/2412.14161) measures completion of 175 professional tasks in a simulated software company. All four are fixed datasets over a single internally consistent system of record, reporting single-run success. Tessera inverts the premise: truth is deliberately fragmented across two systems with symmetric authority, and the score covers per-field provenance, committed refusal, and strict pass^k — failure modes a single-source, single-run environment cannot surface.

**Hallucination, abstention, and knowledge conflict.** This family is Tessera's conceptual ancestry, in three strands. Abstention on unanswerable inputs runs from [SQuAD 2.0](https://arxiv.org/abs/1806.03822)'s adversarially unanswerable questions through [SelfAware](https://arxiv.org/abs/2305.18153)'s detection of uncertainty expressions to the [AbstentionBench](https://arxiv.org/abs/2506.09038) preprint, which finds that scale barely helps abstention and reasoning fine-tuning degrades it. [HaluEval](https://arxiv.org/abs/2305.11747) measures recognition of hallucinated content in given text. The knowledge-conflict strand begins with [Longpre et al.](https://arxiv.org/abs/2109.05052)'s entity-substitution study of parametric-versus-contextual conflict and continues through [ConflictQA](https://arxiv.org/abs/2305.13300), which measures which source a model adopts under constructed counter-memory, and the [ConflictBank](https://arxiv.org/abs/2408.12076) preprint, which scales conflicts to millions of claim–evidence pairs. The closest neighbor to Tessera is the [WikiContradict](https://arxiv.org/abs/2406.13805) preprint: 253 real conflicts between Wikipedia passages of equal trustworthiness, where reflecting the conflict is the correct behavior. Throughout the family, the conflicting evidence is given in the prompt rather than discovered, abstention is detected by judges or uncertainty heuristics, and nothing repeats across trials. Tessera moves the same targets into a tool-using loop: the conflict must be found through MCP calls, the refusal must be the committed final line, and scoring is deterministic under strict pass^k.

**Evaluation frameworks.** Inspect (inspect_ai), from the UK AI Security Institute, is the framework Tessera builds on: composable solvers, native MCP tool calling, and multi-epoch score reducers from which pass^k-style aggregation can be composed. It is a harness, not a benchmark — it ships no enterprise tasks and no abstention metric. [HELM](https://arxiv.org/abs/2211.09110) established multi-axis evaluation — accuracy, calibration, robustness, and four more — over static datasets. These supply the methodology substrate; Tessera adds what neither contains: the deterministically compiled fragmented-org environments, the versioned per-field provenance scorer, and the unresolvable-tie refusal measurement.

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
