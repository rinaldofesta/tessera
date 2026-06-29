# Tessera: a deterministic benchmark for enterprise agent reliability

**Rinaldo Festa** · June 28, 2026 · scorer `det-4` · leaderboard and delegation as of 2026-06-12, scaffold intervention as of 2026-06-28
Repository: <https://github.com/rinaldofesta/tessera> · Protocol: [ADR-0006](adr/0006-meridian-and-the-leaderboard-protocol.md)

## Abstract

Enterprise knowledge is fragmented across systems of record, and the fragments contradict one another: a CRM and a documentation wiki carry different values for the same field, with nothing that gives either precedence. Agents asked questions over this substrate commit confident answers anyway, and the fabricated resolution is the failure that looks like success. We present Tessera, an open benchmark generator: a declarative Blueprint of claims and probes is compiled deterministically into a fragmented synthetic organization, served to the agent under test over the Model Context Protocol (MCP) — the access surface a production agent would use. A deterministic scorer grades the committed answer on three axes — accuracy, per-field provenance read from the agent's real MCP traffic, and committed refusal — under versioned rules (`det-4`), and a frozen comparability protocol keeps published rows comparable: strict pass^k as the headline, executable guards that abort non-comparable configurations, and transcript adjudication of every failing probe. On the public `meridian` org, none of the five evaluated models reliably refuses the symmetric ties as a category: the unresolvable column reads 40/0/0/0/0 at k=3, and the dominant failure is a fabricated tie-break committed as fact. In a single-hop delegation study (same model as producer and consumer), the hop was a faithful conduit: it destroyed no correct refusal (0/27) and relayed every upstream fabrication downstream as settled fact (3/3). A third experiment contrasts the fixed prompt with a refusal-aware scaffold across five factory instances and finds the intervention to be a capability amplifier rather than a substitute: it improves correct refusal significantly and without a significant answering loss for the models that can perceive the conflict (claude-sonnet-4-6 and gpt-4o, the unresolvable column rising 20→88% and 16→48%), while a weaker model pays for the gain in over-refusal and the weakest never reaches the tie. Code, blueprints, logs, and the leaderboard are open; every published row's failing probes are adjudicated from transcripts before publication.

## 1. Introduction

Enterprise knowledge does not live in one place. It fragments across a CRM, a documentation wiki, a renewal tracker, ticket queues — and the fragments disagree. A system of record and a departmental tracker carry different values for the same contract field, with timestamps and authority that give neither precedence. An agent asked a question over this substrate must do more than retrieve: it must reconcile silos, and when the evidence is symmetric — when no honest reading of the sources yields a winner — the reliable behavior is to refuse and escalate, not to produce a confident answer. Fabricating a tie-break is the failure mode that matters in production, because it is the one that looks like success.

Capability is not reliability. A model that answers correctly 2 times in 3 is a demo, not a system: deployed unwatched, it is wrong on a schedule. The metric has to encode this, so Tessera's headline is strict pass^k — a probe counts only if every one of its k repetitions passes. Mean accuracy is reported alongside, as capability when the dice land well; it is never the headline.

What gets graded is equally deliberate. Tessera scores what the agent commits to: its final `ANSWER:` line, not the reasoning above it. The canonical enterprise failure is helpful-sounding analysis — the conflict noticed, the sources weighed, the hedge articulated — followed by a fabricated commitment. An agent that reasons correctly and then commits to an invented value has failed in exactly the way a downstream consumer of the answer cannot detect, so the committed line decides both accuracy and refusal.

One scope statement bounds every claim in this report: Tessera scores policy *execution*, not policy *discovery*. The agent is told the reconciliation policy — a source that declares itself binding wins even over a fresher one; absent declared authority, the most recent wins; refuse where neither rule disambiguates or the record is absent. The question measured is not whether an agent can infer a sensible policy on its own, but whether it executes a stated one reliably, repetition after repetition. Discovery is a separate and harder problem; conflating the two would make results on either uninterpretable.

The thesis of this report is that the instrument is the contribution, and the measurements are the evidence that the instrument works. Concretely, we contribute:

- **An open benchmark generator.** A Blueprint — declarative claims plus probes — is compiled deterministically into a fragmented synthetic organization, served to the agent under test over two MCP servers: the same access surface a production agent would use, with the fragmentation and the contradictions placed by design rather than by accident.
- **A deterministic scorer of the committed answer**, on three axes: accuracy against the committed line, per-field provenance read from the agent's real MCP traffic, and committed refusal. The scorer is versioned (`det-4`), so every published result names the exact rules that produced it.
- **A frozen comparability protocol**: strict pass^k with k owned by the task definition rather than the runner, executable comparability guards that abort non-comparable configurations instead of warning about them, and transcript adjudication of every probe the strict reducer fails — so a failure is diagnosed, not merely counted.
- **Three measured findings.** First, no evaluated model reliably refuses the symmetric ties as a category: the leaderboard's unresolvable column reads 40/0/0/0/0 at k=3, and the dominant failure is a fabricated tie-break committed as fact. Second, in a one-hop producer→consumer study, the delegation hop was a faithful conduit: it laundered every upstream fabrication into downstream settled fact (3/3 relayed) while never destroying a correct refusal (0/27). The hop inherited the decision; it did not audit it. Third, a refusal-aware scaffold — tested against the fixed prompt across five factory instances with a paired McNemar design — is a capability amplifier rather than a substitute: it converts detection of a tie into refusal, significantly and without a significant answering loss, for the models that can already detect it (claude-sonnet-4-6 p = 0.0001, gpt-4o p = 0.004), while it cannot manufacture the detection a weaker model lacks.

The remainder of the report presents related work, the method and protocol, the experiments behind both findings, the limitations that bound what these measurements license, and the future work they motivate.

## 2. Related work

Tessera inherits from six families of prior work; we take each in turn, closing with what it leaves unmeasured.

**Tool-use reliability.** [τ-bench](https://arxiv.org/abs/2406.12045) evaluates an agent operating domain API tools under policy documents while conversing with an LM-simulated user, judged by end-of-conversation database state. It is the origin of pass^k — all k i.i.d. trials of a task must succeed — the metric Tessera adopts as its headline. [τ²-bench](https://arxiv.org/abs/2506.07982) adds dual-control environments in which agent and simulated user both wield tools, and a compositional task generator — a genuine precursor of Tessera's generator, though it composes tasks within fixed hand-built domains. [BFCL](https://proceedings.mlr.press/v267/patil25a.html) checks function-call structure by abstract-syntax-tree (AST) matching at scale and does score abstention when no provided function applies, but reports single-run accuracy with no multi-trial metric. This family pioneered pass^k and task generation; none of it scores per-field provenance against actual tool returns, or refusal when two systems of record disagree with symmetric authority — the measurements Tessera makes central.

**General agent benchmarks.** [AgentBench](https://arxiv.org/abs/2308.03688) measures multi-turn decision-making across eight interactive environments; [GAIA](https://arxiv.org/abs/2311.12983) poses 466 real-world general-assistant questions requiring browsing and tool use, scored against unique ground truth; [WebArena](https://arxiv.org/abs/2307.13854) scores end-to-end functional success on 812 long-horizon tasks in a self-hosted web environment. All three are fixed datasets scored in a single run; WebArena even includes a set of infeasible tasks whose gold answer is "N/A" — single-run abstention — but none of the three poses conflicts between equally authoritative sources, scores provenance against tool returns, or measures repetition. They map what agents can do; Tessera asks whether a narrow set of enterprise behaviors holds up under repetition, per-field provenance checking, and deliberately symmetric cross-source conflicts — the measurements these designs do not make.

**Agent safety and risk.** [ToolEmu](https://arxiv.org/abs/2309.15817) emulates tool execution with an LM and quantifies harmful-side-effect risk with an LM judge across 36 high-stakes toolkits; [AgentHarm](https://arxiv.org/abs/2410.09024) measures whether agents refuse explicitly malicious multi-step tasks — and, like Tessera, is distributed on [inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai). This family scores safety refusal: declining to do harm. Tessera scores epistemic refusal — committed abstention when symmetric evidence makes any answer a fabrication — with a deterministic versioned scorer over real MCP-served environments rather than LM emulation and LM judging.

**Enterprise and work-domain agents.** [CRMArena](https://arxiv.org/abs/2411.02305) places agents in a synthesized Salesforce-style org of sixteen interconnected object types; [CRMArena-Pro](https://arxiv.org/abs/2505.18878) extends it across sales, service, and configure-price-quote (CPQ), and adds a confidentiality-awareness assessment — a refusal measurement, though its target is data leakage, not evidence. [WorkBench](https://arxiv.org/abs/2405.00823) scores 690 workplace tasks deterministically against a unique correct final database state; [TheAgentCompany](https://arxiv.org/abs/2412.14161) measures completion of 175 professional tasks in a simulated software company. All four are fixed datasets over internally consistent environments — one or several services that never contradict one another by design — reporting single-run success. Tessera inverts the premise: truth is deliberately fragmented across two systems with symmetric authority, and the score covers per-field provenance, committed refusal, and strict pass^k — failure modes a single-source, single-run environment cannot surface.

**Hallucination, abstention, and knowledge conflict.** This family is Tessera's conceptual ancestry, in three strands. Abstention on unanswerable inputs runs from [SQuAD 2.0](https://arxiv.org/abs/1806.03822)'s adversarially unanswerable questions through [SelfAware](https://arxiv.org/abs/2305.18153)'s detection of uncertainty expressions to [AbstentionBench](https://arxiv.org/abs/2506.09038) (NeurIPS 2025), which finds that scale barely helps abstention and reasoning fine-tuning degrades it. [HaluEval](https://arxiv.org/abs/2305.11747) measures recognition of hallucinated content in given text. The knowledge-conflict strand begins with [Longpre et al.](https://arxiv.org/abs/2109.05052)'s entity-substitution study of parametric-versus-contextual conflict and continues through [ConflictQA](https://arxiv.org/abs/2305.13300), which measures which source a model adopts under constructed counter-memory, and [ConflictBank](https://arxiv.org/abs/2408.12076), which scales conflicts to millions of claim–evidence pairs. The closest neighbor to Tessera is [WikiContradict](https://arxiv.org/abs/2406.13805) (NeurIPS 2024): 253 real conflicts between Wikipedia passages of equal trustworthiness, where reflecting the conflict is the correct behavior. Throughout the family, the conflicting evidence is given in the prompt rather than discovered, and nothing repeats across trials; in its LLM-era members, abstention is detected by judges or uncertainty heuristics (SQuAD 2.0 scored a committed no-answer deterministically — the spirit Tessera carries into the agent loop). Tessera moves the same targets into a tool-using loop: the conflict must be found through MCP calls, the refusal must be the committed final line, and scoring is deterministic under strict pass^k.

**Evaluation frameworks.** Inspect (inspect_ai), from the UK AI Security Institute, is the framework Tessera builds on: composable solvers, native MCP tool calling, and multi-epoch score reducers from which pass^k-style aggregation can be composed. It is a harness, not a benchmark — it ships no enterprise tasks and no abstention metric. [HELM](https://arxiv.org/abs/2211.09110) established multi-axis evaluation — accuracy, calibration, robustness, and four more — over static datasets. These supply the methodology substrate; Tessera adds what neither contains: the deterministically compiled fragmented-org environments, the versioned per-field provenance scorer, and the unresolvable-tie refusal measurement.

## 3. Method

### 3.1 Blueprint: claims, probes, and a conflict taxonomy

The method has one organizing principle: every design decision exists because a concrete failure — observed in this project's own history — would otherwise be mis-scored. Each subsection below states the decision, names the failure, and, where one is on record, cites the architecture decision record (ADR). The first decision is the data shape itself.

A benchmark instance is a Blueprint: a declarative description of a fragmented organization, made of claims and probes. A claim is an atomic fact — subject, predicate, value — that lives in exactly one silo, optionally timestamped and optionally carrying declared authority; a rendering directive materializes it either as a structured CRM field or as a sentence in a markdown document. A probe is a question over those claims that declares its conflict type, its expected behavior (answer or refuse), the expected answer where one exists, and the claims an agent must consult to earn provenance credit.

Conflicts come in exactly four kinds. `none`: the silos agree, or only one speaks. `resolvable`: the silos disagree but a stated rule decides — the most recent assertion wins, or a source with declared binding authority does. `unresolvable`: the silos disagree with symmetric authority and nothing disambiguates; the correct behavior is committed refusal. `void`: no record exists anywhere; the correct behavior is again refusal. This taxonomy is what lets §4 report refusal as a per-category measurement rather than an impression: an unresolvable probe is constructed so that any committed answer is a fabrication.

Model validators enforce coherence at load time (`src/tessera/models.py`): a refuse-probe must carry no expected answer and an answer-probe must carry one; a resolvable probe must name its resolution rule; a void probe must expect refusal and reference no claims; every reference and expected source must resolve to an existing claim, and claim ids must be unique. The failure these validators catch is the quiet one in hand-authored datasets: a probe whose metadata encodes contradictory grading expectations — labeled refuse while carrying an answer to match, or labeled void while pointing at records that exist. Such a blueprint does not produce a subtly wrong score; it fails validation and never runs.

The public benchmark instance is the `meridian` org: 10 accounts, 47 claims, 22 probes, designed so that each conflict category is measured by several probes rather than one. §4 gives the per-category split.

### 3.2 Deterministic compilation into a fragmented environment

A compiler turns the org definition into the environment the agent actually touches: a CRM `db.json` mapping subject → {predicate → {value, asserted_at}}, one markdown document per prose claim, and a `manifest.json` mapping every claim id to its silo, artifact, and field-level locator — the bridge the scorer later uses to resolve a recorded tool call back to a specific claim. Two MCP stdio servers expose the result: a CRM lookup tool (`crm_lookup`) and a docs reader (`docs_search`, `docs_get_file`). The servers are deliberately dumb file servers; the compiler is the only component that understands fracture semantics — it even rejects intra-silo collisions, so every contradiction is cross-silo, placed by the blueprint and never improvised by the harness.

Compilation is deterministic and pure, and both properties are pinned by tests (`tests/test_compiler.py`): the same blueprint always yields byte-identical structured artifacts (the CRM database and the manifest), and artifact construction performs no I/O. The failure this catches is environment drift — two runs of the "same" benchmark facing subtly different orgs, which would silently invalidate every cross-run comparison §3.4 depends on. With a deterministic compiler, a published row's environment is a function of the blueprint and nothing else.

One line restates the scope from §1, because this is where it is materialized: the task prompt states the reconciliation policy — a source that declares itself binding overrides the others; otherwise the most recent wins; refuse when neither rule disambiguates or no record exists. Tessera scores policy execution, not policy discovery.

### 3.3 Scoring the committed answer (`det-4`)

The deterministic engine scores three axes — accuracy, provenance, committed refusal — on the answer the agent commits to, and every rule in it exists because an earlier rule mis-scored a real transcript.

**The committed line decides accuracy and refusal** ([ADR-0003](adr/0003-score-the-committed-answer.md)). The task prompt and the submit tool's own description mandate a final `ANSWER: <value>` line, with `ANSWER: cannot determine` as the abstention form; the last such line wins, since models self-correct. When the line exists, only it is graded — on both axes. The failure this catches is abstain-then-hallucinate: under the first engine's whole-transcript keyword scan, a cautious hedge followed by a fabricated committed value was credited as a refusal — the exact fabricate-instead-of-refuse failure Tessera exists to surface, scored as its opposite. Under `det-4`, a line that leads with the abstention (`ANSWER: cannot determine`) scores as refusal; a line that commits a value and only then appends a hedge scores as a commitment, as does a committed value beneath hedged reasoning. Symmetrically, transparent hedging above a correct committed answer is never penalized.

**Accuracy matching is boundary-guarded.** Raw substring matching — the first engine's actual behavior — credited "4 hours" inside "24 hours" and "15%" inside "115%". The `det-4` pattern rejects adjacent alphanumerics, and digit-leading values also reject a preceding dot.

**Provenance is per-field and response-based** ([ADR-0005](adr/0005-per-field-crm-provenance.md)). Each recorded tool call is paired with its result via `tool_call_id`, and a CRM claim is credited only when its predicate is a key of the record the lookup actually returned; `NOT_FOUND`, errored, and unanswered calls credit nothing. The failure: the earlier scorer credited the call, not the response — an agent earned provenance for a lookup that returned nothing, and a single lookup on a subject credited every CRM claim about it. Credit now means the field's data demonstrably reached the agent's context. Docs credit stays call-based: one file per prose claim; the path is the address. The `docs_search` excerpt is the rendered claim sentence and can surface the answer value, but provenance is credited only by `docs_get_file` — answering from the excerpt alone earns no docs provenance. This is a deliberate "consult the claim means open its file" rule, not a leak: in practice docs provenance runs 98–100%, so models do open the file.

**Without an `ANSWER:` line, a documented fallback applies**: the expected value must appear in the response, and no distractor value may appear after its last mention — last-mention-wins, so the ideal transparent answer (cite the stale value, then commit to the right one) passes, while committing to the stale value does not. Distractors are derived mechanically from the blueprint's conflicting (subject, predicate) claim groups, never hand-listed. The fallback is harsher on transparent prose: it grades the whole response under an ordering constraint rather than one committed line, and its residual gaps ("X, not Y" negations, date-format paraphrases) are documented in `src/tessera/evals/scoring.py`. Because the fallback is both harsher and imperfect, whether a row rode it is itself published: `answer_format_ok` is stamped into every score and surfaces per row as `ANSWER fmt`.

**Scoring semantics are versioned.** Every score records its `scorer_version` — `det-4` today — and any semantic change bumps the version and re-partitions trend comparisons, because rule changes move rates for reasons unrelated to the models. An LLM-judged engine (`llm-2`), which shares the deterministic provenance signal and refuses to run with a grader equal to the model under test, exists as an independent cross-check; every published leaderboard row is scored by `det-4`.

### 3.4 The comparability protocol

Comparability is the protocol's product, and its rules are executable or gated, not editorial.

**k lives in the task** ([ADR-0001](adr/0001-k-lives-in-the-task.md)). The task definition owns both the epoch count and the strict `pass_k` reducer through a single parameter, so the two cannot diverge. The failure on record: inspect_ai merges them independently, and an eval-level epochs override — forwarded by this project's own product UI — changed the count while silently keeping the task's pinned reducer. The published number would have been pass^3 computed over a different number of repetitions: a metric whose name no longer means what it says.

**The headline is strict pass^k at k=3**: a probe counts only if all k repetitions pass. Mean accuracy is published alongside, as capability — never as the headline (§1).

**Every row is frozen to the same protocol**: the deterministic engine and the full probe set ([ADR-0006](adr/0006-meridian-and-the-leaderboard-protocol.md)); the task prompt is a single shared constant, so per-model prompt tuning has no mechanism to exist. The freeze is enforced by code, not convention: the `tessera-leaderboard` generator refuses to mix rows with differing `scorer_version`, org, or k, aborting with a hard error — one leaderboard, one protocol — rather than emitting a table with a footnote.

**The blueprint is public — honesty over purity** ([ADR-0006](adr/0006-meridian-and-the-leaderboard-protocol.md)). `meridian` is the answer key by design: anyone can reproduce a row with no grader key, and for the same reason training-data contamination becomes likelier over time. Rows are date-stamped, the risk is stated rather than silent, and seeded value-rotation variants are the planned mitigation once contamination becomes measurable.

**Adjudication gates publication.** Every probe that fails strict pass^k in a published row — one failed epoch zeroes the probe — is adjudicated from its transcript before the row ships, so a failure is diagnosed, not merely counted. The gate has teeth: adjudication of the first `meridian` baseline surfaced a harness flaw — an agent's wrong field-name guess came back as an ambiguous empty record — so the tool was fixed to name the unknown field and list the available ones, the way a real API would, and the run was redone. Numbers are accepted only after that gate.

## 4. Experiment 1: a five-model leaderboard

The first experiment is the instrument applied as intended: one org, one frozen protocol, five models, every number traceable to a logged run.

**Setup.** The benchmark instance is the `meridian` org of §3.1 — 22 probes over 10 accounts and 47 claims, split 6 `none`, 6 `resolvable`, 5 `unresolvable`, 5 `void`. Every row was produced under the protocol of §3.4: the `det-4` engine, the full probe set, strict pass^3 at k=3 with mean accuracy alongside. The five models span three serving regimes — two Anthropic API models (claude-sonnet-4-6, claude-haiku-4-5), two OpenAI API models (gpt-4o, gpt-4o-mini), and one open-weights model, qwen3.5 at 9.7B parameters and Q4_K_M quantization, run locally via Ollama. Run dates are stamped per row: claude-sonnet-4-6 on 2026-06-11, the other four on 2026-06-12.

| # | Model | pass^3 | mean | none | resolvable | unresolvable | void | ANSWER fmt | scorer | run date |
|--:|---|--:|--:|--:|--:|--:|--:|--:|---|---|
| 1 | anthropic/claude-sonnet-4-6 | **86.4%** | 90.9% | 100% | 100% | 40% | 100% | 98.5% | det-4 | 2026-06-11 |
| 2 | anthropic/claude-haiku-4-5 | **54.5%** | 68.2% | 66.7% | 66.7% | 0% | 80% | 3% | det-4 | 2026-06-12 |
| 3 | ollama/qwen3.5:latest | **45.5%** | 71.2% | 83.3% | 33.3% | 0% | 60% | 43.9% | det-4 | 2026-06-12 |
| 4 | openai/gpt-4o | **45.5%** | 54.5% | 0% | 83.3% | 0% | 100% | 22.7% | det-4 | 2026-06-12 |
| 5 | openai/gpt-4o-mini | **27.3%** | 40.9% | 0% | 16.7% | 0% | 100% | 92.4% | det-4 | 2026-06-12 |

*The table reproduces [`docs/leaderboard.md`](leaderboard.md); the published `notes` column is carried into the prose below.*

**The headline is the `unresolvable` column, and it reads 40/0/0/0/0.** Each of the five unresolvable probes is a symmetric tie: two systems of record disagree with equal authority, nothing in the stated policy disambiguates, and the policy's own instruction is to refuse. By construction (§3.1), any committed value on these probes is wrong. Under strict pass^3, the best model refuses reliably on two of the five ties (40%); the other four models refuse reliably on none of them. Transcript adjudication identifies the dominant failure: a fabricated tie-break committed as fact — the failure mode §1 named as the one that looks like success.

The per-model profiles, each carrying its published note:

**claude-sonnet-4-6** (strict 86.4%, mean 90.9%) is perfect on `none`, `resolvable`, and `void`; its entire distance from a perfect row is the `unresolvable` column at 40%. Contract compliance is near-total (ANSWER fmt 98.5%), so the tie failures are behavioral, not clerical.

**claude-haiku-4-5** (54.5% / 68.2%) ignores the committed-answer contract — ANSWER fmt 3% — so its grades ride the documented fallback path of §3.3 rather than the committed line. Behaviorally, it fabricates a tie-break on all five symmetric ties; the remaining categories sit at 66.7% (`none`, `resolvable`) and 80% (`void`) — partial reliability everywhere, none on the ties.

**qwen3.5** (45.5% / 71.2%) is a diligent reader — provenance 98% — and the table's least stable row: a mean of 71.2% against a strict 45.5% is the widest mean-to-strict gap in the table — capability that does not survive repetition. Of its 12 failed probes, 5 are fallback strictness on format-noncompliant but substantively correct answers (ANSWER fmt 43.9%) — the case behind the `det-5` candidate below.

**gpt-4o** (45.5% / 54.5%) posts the table's most legible signature: `none` at 0% against `void` at 100%. Adjudication traces it to the cross-silo joins: the model skips the CRM leg of the join and does not adapt when a wrong field-name guess draws the `_available_fields` feedback the CRM returns precisely for that case — 8 of its 12 failed probes.

**gpt-4o-mini** (27.3% / 40.9%) fails both the joins (`none` 0%, `resolvable` 16.7%) and all five ties (`unresolvable` 0%) while honoring the answer contract at 92.4% — format discipline without reliability, and the row that shows most plainly why the two are separate columns.

**Adjudication disclosure.** Per the gate of §3.4, every probe that failed strict pass^3 in every row was adjudicated from its transcript before publication: 38 verdicts across the three API-model rows run on 2026-06-12 — 36 behavioral failures and 2 grades-on-wording under the documented contract — plus 12 on qwen3.5, of which 5 are the documented fallback grading format-noncompliant but substantively correct answers. (claude-sonnet-4-6's row had already passed the same gate at its 2026-06-11 baseline.) The decision on record is to publish with structural disclosure — the ANSWER fmt column in every row — rather than bend the scorer per model. A hardening of the fallback, `det-5`, is a recorded candidate (§7, §8); under it, qwen3.5's strict score would read approximately 68.2%.

Every row above is reproducible with a single `inspect eval` invocation plus `tessera-leaderboard` over the resulting logs; the exact commands live in [`docs/leaderboard.md`](leaderboard.md).

## 5. Experiment 2: reliability under delegation

Enterprise agents increasingly hand work to other agents: one researches, another acts on the findings. The second experiment asks whether the reliability §4 measured survives that handoff — not as an abstract degradation rate, but as two specific failure modes at the producer→consumer boundary. The hop can destroy a correct refusal: a producer's committed abstention overridden by a downstream agent that commits anyway. Or it can launder a fabrication: an upstream invented value relayed downstream as settled fact, arriving stripped of whatever might have marked it as a guess.

**Design.** A producer agent with the MCP tools researches the org and submits a brief; a tool-less consumer agent receives only the question plus the producer's submitted answer, and commits the final answer. Same model on both stages (claude-sonnet-4-6), same prompt contract — the consumer carries the producer's reconciliation policy and `ANSWER:` line obligations — and the same `det-4` scorer; the only variable is the hop. The two stages' transcripts are merged into one, which is what lets `det-4` apply unchanged: provenance reads the producer's real MCP traffic (1.0 across all 66 epochs of the delegated run), while accuracy and refusal read the consumer's committed line. Two hop flags recorded per refuse-probe epoch classify the boundary: `flag_dropped` — the producer refused, the consumer committed anyway — and `conflict_laundered` — the producer fabricated, the consumer relayed it.

**Why not the framework's native `handoff()`** ([ADR-0007](adr/0007-delegation-mvp.md)). We verified against the installed version of inspect_ai that `handoff()` cannot satisfy the experiment's two invariants at once. Its default content-only output filter converts the sub-agent's tool calls to plain text and its tool messages to user messages, so the producer's traffic would not survive as structured tool events and provenance would always score zero. Disabling the filter restores the tool events, but `handoff()` shares one conversation between the stages, so the restored events reach the consumer too: the scorer's view and the consumer's view cannot diverge, and once the raw tool results leak to the consumer, nothing has actually been delegated. The implementation is therefore a custom two-stage chain composed through the framework's agent-composition API — two `react()` agents sequenced via `inspect_ai.agent.run()` — with the producer's submitted brief carried to the consumer, and to the scorer, through the per-sample store. The producer is exactly the direct task's agent, so §4's claude-sonnet-4-6 row is the clean counterfactual.

The pair, under the same comparability guard as §4:

| # | Run | pass^3 | mean | none | resolvable | unresolvable | void | scorer | run date |
|--:|---|--:|--:|--:|--:|--:|--:|---|---|
| 1 | claude-sonnet-4-6 (delegated) | **90.9%** | 95.5% | 100% | 100% | 60% | 100% | det-4 | 2026-06-12 |
| 2 | claude-sonnet-4-6 (direct) | **86.4%** | 90.9% | 100% | 100% | 40% | 100% | det-4 | 2026-06-11 |

And the hop flags, over the 30 refuse-probe epochs of the delegated run:

| Outcome | Count | Reading |
|---|--:|---|
| producer refused → consumer refused | 27 | the flag survived the hop |
| producer refused → consumer committed (`flag_dropped`) | **0** | the hop never destroyed a correct abstention |
| producer fabricated → consumer relayed (`conflict_laundered`) | **3** | every upstream fabrication arrived downstream as settled fact |
| producer fabricated → consumer refused (rescue) | 0 | the hop never repaired one either |

Four findings:

1. **The hop is a faithful conduit — and that is the risk.** The consumer never overrode a correct refusal (`flag_dropped` 0/27: no producer refusal was overridden, including the 12 on the unresolvable ties) and never challenged a fabrication (`conflict_laundered` 3/3). Delegation neither degraded nor improved the decision; it inherited it. A tie-break fabricated at stage one arrives at stage two dressed as a finding.

2. **The laundering is articulate.** On `q_quill_renewal` the consumer did not just relay the producer's invented precedence — it rationalized it: "the analyst applied a tiebreaker by favoring the dedicated renewal tracker … which is a reasonable judgment call." In the quoted case, the answer grew more confident as it moved away from the evidence — whether that compounds over deeper chains is a §8 question.

3. **The headline delta is producer-side sampling noise, not a hop effect.** The delegated 90.9% over the direct 86.4% does not mean delegation improved reliability. The producer is the direct task's exact agent; in this run it fabricated in 3/15 unresolvable epochs against 5/15 in the baseline, and a 5-probe category at k=3 swings by that much. The hop-flag table, not the topline, is the result.

4. **Scope.** One hop, a tool-less consumer, the same model on both stages — the explicit non-goals of ADR-0007 bound the claim. The questions this baseline makes askable — a weaker consumer, a tool-using consumer, deeper chains — are taken up in §8.

Both tables reproduce [`docs/delegation.md`](delegation.md), which carries the exact `inspect eval` and `tessera-leaderboard` commands to regenerate the pair.

## 6. Experiment 3: the refusal-aware scaffold

Experiment 1 measured reliability under one fixed prompt and the unresolvable column read 40/0/0/0/0. The third experiment asks whether that failure is partly a property of the *scaffold* rather than only of the models, by contrasting two prompts that differ in exactly one block. The baseline scaffold (B0) is the Experiment 1 prompt, kept byte-identical: the reconciliation policy plus a single generic refusal nudge. The refusal-aware scaffold (R1) replaces that one sentence with an explicit procedure that turns the four-type taxonomy into an action rule — answer when the sources agree or only one speaks; resolve and state the rule when one source is binding or, absent authority, more recent; refuse and escalate, rather than invent a tie-break, when the sources disagree with equal authority and nothing breaks the tie; refuse the absent record. R1 names the procedure and the stakes of refusing, not which probes are ties — those the agent still discovers by reading the silos — so the experiment stays within the policy-execution scope of §3.2. Both prompts are reproduced verbatim in [ADR-0009](adr/0009-refusal-aware-scaffold-intervention.md).

**Design.** A single org realises each conflict type with five probes, too few to test an intervention, so the contrast runs across five instances of the meridian family using the factory of §3.4 ([ADR-0008](adr/0008-scenario-factory-and-holdout-protocol.md)): the authored org (seed 0) and four variants (seeds 1–4), each re-dealing the conflict graph and synthesizing fresh values while holding the 6/6/5/5 category counts fixed. That is 110 probe-instances per model per arm, paired per (instance, probe) on strict pass^3 and compared with an exact McNemar test over the discordant pairs. H1₂'s claim is conjoint — a refusal gain on the unresolvable and void probes *without* a significant answering loss on the none and resolvable probes — so it is tested on the two disjoint subsets separately, which keeps a gain bought by over-refusal visible rather than netted away. Four API models were run; the open-weights qwen3.5 row was not re-run under both arms. The B0 arm reproduces the Experiment 1 leaderboard within the sampling noise of a five-probe category at k=3.

| Model | arm | net pass^3 | none | resolvable | unresolvable | void | McNemar (helped/hurt) | exact p |
|---|---|--:|--:|--:|--:|--:|:--:|--:|
| claude-sonnet-4-6 | B0 | 75.5% | 90% | 86.7% | 20% | 100% | | |
| claude-sonnet-4-6 | **R1** | **95.5%** | 93.3% | 100% | **88%** | 100% | 24 / 2 | **< 0.0001** |
| gpt-4o | B0 | 44.5% | 0% | 73.3% | 16% | 92% | | |
| gpt-4o | **R1** | **52.7%** | 0% | 73.3% | **48%** | 96% | 10 / 1 | **0.012** |
| claude-haiku-4-5 | B0 | 52.7% | 53.3% | 63.3% | 4% | 88% | | |
| claude-haiku-4-5 | R1 | 54.5% | 53.3% | 43.3% | 36% | 88% | 17 / 15 | 0.86 |
| gpt-4o-mini | B0 | 32.7% | 0% | 36.7% | 0% | 100% | | |
| gpt-4o-mini | R1 | 29.1% | 0% | 23.3% | 0% | 100% | 2 / 6 | 0.29 |

**The scaffold is a capability amplifier, not a substitute.** For the two more capable models R1 is a large, significant gain. claude-sonnet-4-6 rises 75.5% → 95.5%: on the refusal subset it helps eighteen probe-instances and harms one (p = 0.0001), and on the answerable subset it harms none of consequence (six helped, one harmed, p = 0.125, a non-significant gain), so the conjoint claim of H1₂ holds in full. gpt-4o shows the same pattern more modestly: net 44.5% → 52.7%, refusal subset 9/0 (p = 0.004), answerable subset unchanged (p = 1.0). The mechanism is the unresolvable column — Sonnet 20% → 88%, gpt-4o 16% → 48% — exactly the column on which Experiment 1 found every model fabricating. For the weaker models the gain is paid for or unreachable. claude-haiku-4-5 improves significantly on the ties (refusal subset 9/1, p = 0.022; unresolvable 4% → 36%) but loses an almost equal amount on resolvable (63.3% → 43.3%, fourteen harmed against eight helped, not significant on its own at p = 0.29), so net behavior is unmoved and the overall paired test is indistinguishable from chance (p = 0.86). gpt-4o-mini fails the cross-silo joins upstream (none 0% under either arm), never reaches a recognizable tie (unresolvable 0% → 0%), and H0₂ is retained. Naming the taxonomy converts detection into refusal for a model that can already detect the conflict; it cannot manufacture the detection.

**Holdout.** To rule out that the effect is tuned to instances seen while writing the scaffold, claude-sonnet-4-6 was re-run on a *withheld* factory seed under the ADR-0008 commitment. The commitment `df55a190…331ce82` (factory_version `fac-1`) was recorded before the run; the reveal `{seed = 31337, salt, fac-1}` recomputes it (`verify → True`) and regenerates the exact org and answer key. On that committed, previously unseen instance the effect replicates: net 86.4% → 95.5%, unresolvable 40% → 100%. The full tables, the McNemar decomposition, and the commitment/reveal are in [docs/scaffold.md](scaffold.md).

## 7. Limitations

Five limitations bound what the measurements above license. None retracts a finding; each states what the finding does not cover.

**One org.** Every published row measures `meridian`: one blueprint, 10 accounts, 47 claims, 22 probes. With five unresolvable probes, the headline column moves in 20-point steps under strict pass^3 — claude-sonnet-4-6's 40% is two ties of five, arithmetic granularity rather than a fine-grained rate. Breadth is the generator's job, and the generator is built; but breadth is not yet measured, and the published rows characterize a single org.

**The public blueprint is the answer key.** §3.4 chose honesty over purity: anyone can reproduce a row with no grader key, and for the same reason `meridian`'s contents can enter training corpora. Date-stamped rows and seeded value-rotation variants are a mitigation, not a solution; contamination becomes likelier over time, and a future row's improvement may partly be memorization. *(The seeded-variant generator and a salted-commitment holdout protocol have since shipped — [ADR-0008](adr/0008-scenario-factory-and-holdout-protocol.md), 2026-06-19 — postdating this report's 2026-06-12 results.)*

**Fallback strictness.** 5 of qwen3.5's 12 failed probes are the documented fallback (§3.3) grading format-noncompliant but substantively correct answers (§4): on that row, part of the strict–mean gap is set by the scorer's strictness rather than the model's behavior. The `det-5` hardening is a recorded candidate; per §3.3 and ADR-0006, shipping it bumps `scorer_version` and re-runs the whole protocol — every row, same scorer version — which is why the change is deliberate rather than already made.

**The delegation study is small.** One model, one hop, a tool-less consumer, 30 refuse-probe epochs, 3 laundering events. The 3/3 laundering and 0/27 dropped-refusal counts are exact for this run and directional beyond it; they motivate the follow-ups in §8; they do not establish a rate.

**The intervention is established on a small panel.** Four API models, one org family (five instances), the deterministic engine only; the open-weights row is not re-run under both scaffolds. The capability-amplifier reading is consistent across every model tested but rests on four points, and the over-refusal cost on the middle of the range shows the refusal-aware scaffold is not strictly dominant — on a low-capability model it can trade silent error for over-refusal without improving net behavior.

**Policy execution, not discovery.** The scope statement of §1, restated as a limitation: every probe hands the agent the reconciliation policy. These results say nothing about whether an agent can infer a sensible policy from a fragmented org unaided — a separate and harder problem.

## 8. Future work

Four lines of work follow from the limitations.

**Seeded blueprint variants** — the contamination answer: compile seeded value-rotations of `meridian`, so a row can be reproduced against an answer key that postdates any training cutoff, per the mitigation in §3.4. *(Shipped since this report: `generate_variant(seed)` and the salted-commitment holdout protocol — [ADR-0008](adr/0008-scenario-factory-and-holdout-protocol.md). The remaining work is a live leaderboard row produced on a withheld seed.)*

**Delegation follow-ups.** The §5 baseline makes three questions askable: a weaker or cross-model consumer (does laundering worsen when the consumer cannot evaluate the brief?); a tool-using consumer (does independent re-verification catch laundered fabrications?); and chains deeper than one hop.

**Scaffold refinement.** The §6 over-refusal cost — the refusal-aware scaffold's gain on the unresolvable ties bleeding into the resolvable probes on weaker models — motivates a scaffold that keeps the refusal gain without depressing correct answering, perhaps by separating the instruction to *detect* a conflict from the instruction to *refuse* it, plus broader coverage (the open-weights row under both arms and org families beyond meridian).

**Fallback hardening (`det-5`).** The recorded candidate of §4, under the constraint stated in §7.

**Growing the leaderboard.** More models under the frozen protocol; community rows — a `meridian` run on an unmeasured model, adjudicated before it ships — follow the procedure in [CONTRIBUTING.md](../CONTRIBUTING.md).

## References

### External work

- **τ-bench** — ICLR 2025 — <https://arxiv.org/abs/2406.12045>
- **τ²-bench** — arXiv 2025 — <https://arxiv.org/abs/2506.07982>
- **BFCL (Berkeley Function-Calling Leaderboard)** — ICML 2025 (PMLR 267) — <https://proceedings.mlr.press/v267/patil25a.html>
- **AgentBench** — ICLR 2024 — <https://arxiv.org/abs/2308.03688>
- **GAIA** — ICLR 2024 — <https://arxiv.org/abs/2311.12983>
- **WebArena** — ICLR 2024 — <https://arxiv.org/abs/2307.13854>
- **ToolEmu** — ICLR 2024 — <https://arxiv.org/abs/2309.15817>
- **AgentHarm** — ICLR 2025 — <https://arxiv.org/abs/2410.09024>
- **CRMArena** — NAACL 2025 — <https://arxiv.org/abs/2411.02305>
- **CRMArena-Pro** — arXiv 2025 — <https://arxiv.org/abs/2505.18878>
- **WorkBench** — COLM 2024 — <https://arxiv.org/abs/2405.00823>
- **TheAgentCompany** — arXiv 2024 — <https://arxiv.org/abs/2412.14161>
- **SQuAD 2.0** — ACL 2018 — <https://arxiv.org/abs/1806.03822>
- **SelfAware** — ACL 2023 Findings — <https://arxiv.org/abs/2305.18153>
- **AbstentionBench** — NeurIPS 2025 — <https://arxiv.org/abs/2506.09038>
- **HaluEval** — EMNLP 2023 — <https://arxiv.org/abs/2305.11747>
- **Longpre et al. (Entity-Based Knowledge Conflicts in QA)** — EMNLP 2021 — <https://arxiv.org/abs/2109.05052>
- **ConflictQA** — ICLR 2024 — <https://arxiv.org/abs/2305.13300>
- **WikiContradict** — NeurIPS 2024 (Datasets and Benchmarks Track) — <https://arxiv.org/abs/2406.13805>
- **ConflictBank** — NeurIPS 2024 (Datasets and Benchmarks Track) — <https://arxiv.org/abs/2408.12076>
- **Inspect (inspect_ai)** — GitHub, UK AI Security Institute — <https://github.com/UKGovernmentBEIS/inspect_ai>
- **HELM** — arXiv 2022; TMLR 2023 — <https://arxiv.org/abs/2211.09110>

### Internal artifacts

- **ADR-0001 — the epoch count and the pass^k reducer live together in the task** — [adr/0001-k-lives-in-the-task.md](adr/0001-k-lives-in-the-task.md)
- **ADR-0003 — the deterministic engine scores the committed answer** — [adr/0003-score-the-committed-answer.md](adr/0003-score-the-committed-answer.md)
- **ADR-0005 — per-field CRM provenance** — [adr/0005-per-field-crm-provenance.md](adr/0005-per-field-crm-provenance.md)
- **ADR-0006 — meridian as the public reference org; the leaderboard protocol** — [adr/0006-meridian-and-the-leaderboard-protocol.md](adr/0006-meridian-and-the-leaderboard-protocol.md)
- **ADR-0007 — reliability under delegation: a two-stage chain, not `handoff()`** — [adr/0007-delegation-mvp.md](adr/0007-delegation-mvp.md)
- **ADR-0008 — the scenario factory and the holdout protocol** — [adr/0008-scenario-factory-and-holdout-protocol.md](adr/0008-scenario-factory-and-holdout-protocol.md)
- **ADR-0009 — the refusal-aware scaffold intervention** — [adr/0009-refusal-aware-scaffold-intervention.md](adr/0009-refusal-aware-scaffold-intervention.md)
- **Leaderboard** — published rows and the commands that regenerate them — [leaderboard.md](leaderboard.md)
- **Delegation study** — the delegated pair and the hop-flag table — [delegation.md](delegation.md)
- **Scaffold intervention** — B0 vs R1, the paired McNemar tables, and the holdout reveal — [scaffold.md](scaffold.md)
- **Contributing guide** — the community leaderboard-row protocol — [CONTRIBUTING.md](../CONTRIBUTING.md)
