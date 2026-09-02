# Tessera synthetic-to-real transfer study

> **Status: DRAFT. This document is not registered and no scored run may start from it.**
> Registration requires the frozen configuration table, hashes, a signed public Git tag,
> and a public OSF Open-Ended Registration.

## Question

Do configuration rankings on a Tessera-generated organization transfer to rankings on a
private production matching eval when the model, harness, scaffold, sampling, tool budget,
and output contract are held fixed?

The study covers one production domain. With 7 to 10 configurations it can detect strong
transfer; moderate transfer may remain inconclusive. A negative or inconclusive result will
be published with the same artifacts as a positive result.

## Authorization gates

No private production-eval data may be inspected or processed for this study until both
gates pass:

1. Written authorization from the data controller covers the new validation purpose, allowed
   outputs, retention, and whether the organization may be named.
2. Every deal contributing to the golden set has been checked against its MSA for secondary
   analytical use.

If approval permits publication, the public payload is limited to configuration-level ranks,
uncertainty, correlation, and pattern-level task categories containing at least five tasks.
It contains no source text, client or candidate name, exact date-role combination, or other
identifying metadata. Named attribution requires separate written approval.

If either gate fails, no production-derived public claim is made. The public study moves to
a design partner under a new registration.

## Frozen panel

Membership is determined before the first scored run:

- 7 to 10 single-model configurations runnable unchanged on both suites.
- At least three providers, at least two pinned local models, and at least one mid-tier model.
- One configuration identity consists of model snapshot ID, harness commit, scaffold hash,
  sampling parameters, tool budget, output-contract hash, and adapter hash.
- A configuration unavailable after registration is dropped and disclosed. It is never
  replaced.
- If the eligible intersection contains fewer than 7 or more than 10 configurations, the
  study stops. A revised registration must precede any run.

The exact table below must replace `PENDING` before registration:

| config ID | provider | model snapshot | local/API | harness | scaffold | sampling | tool budget | output contract |
|---|---|---|---|---|---|---|---:|---|
| PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

Each registered configuration runs at least three repetitions per task. All scored runs must
finish within four weeks of the freeze. Repetitions are collapsed to each suite's registered
task-level outcome before analysis.

## Frozen instruments

- **Tessera:** `factory_version=fac-1`, exact package commit and prompt hashes recorded below.
  The primary score is the existing strict overall `pass^k`: a probe passes only when all
  registered repetitions pass accuracy, provenance, and correct-refusal checks.
- **Production matching eval:** the existing composite formula and weights are copied here
  before the first run. The golden-set digest is published; no source content is published.
- `fac-1` is frozen before anyone inspects TaaS for generator patterns. Approved patterns may
  inform `fac-2` only after this study and require a new holdout or partner domain.

Freeze record, completed before registration:

| artifact | SHA-256 / commit |
|---|---|
| Tessera release commit | PENDING |
| `fac-1` schema and prompts | PENDING |
| shared harness and adapters | PENDING |
| configuration matrix | PENDING |
| production scorer and composite weights | PENDING |
| production golden set | PENDING |

## Confirmatory analysis

The primary statistic is Kendall's tau-b between the two configuration rankings. The
confirmatory gate passes when a one-sided bootstrap-over-tasks 95% lower bound is above zero.

- Draw 10,000 bootstrap samples with the registered seed. Both values are mandatory analyzer
  inputs; neither defaults when absent.
- Resample tasks independently within each suite and use the same sampled task indices for
  every configuration in that suite.
- Exclude a draw only when tau-b is undefined because a sampled suite has no rank variance.
  At least 9,500 of 10,000 draws must be identifiable; otherwise the analysis fails.
- Use the fifth percentile of valid draws as the one-sided 95% lower bound.
- Freeze both suites' primary scoring formulas. Alternative weights are sensitivity analyses.

The public claim is bound before the run:

| outcome | permitted sentence |
|---|---|
| lower bound > 0 and tau >= 0.6 | Rankings transfer. |
| lower bound > 0 and 0.3 <= tau < 0.6 | Moderate transfer evidence in one domain. |
| lower bound > 0 and tau < 0.3 | Weak positive evidence; insufficient for a transfer claim. |
| lower bound <= 0 | Transfer not demonstrated. |

## Registered secondary outputs

- Top-three overlap, descriptive only. Exactly three configurations are returned; a score tie
  at the boundary is disclosed and broken by natural ascending configuration ID, with numeric
  runs compared as integers (`config-9` precedes `config-10`). Reported ranks use standard
  competition ranking (`1, 1, 3` after a tie).
- Decisive-pair concordance. A pair is decisive **if and only if its two-sided 95% score
  intervals are disjoint on both suites**. The concordant count, decisive denominator, rate,
  and pair list are always reported, including a denominator of zero.
- Per-axis and alternative-weight correlations, labeled exploratory.

The raw-data-free analyzer is `python -m research.transfer.cli`. Its input contract and output are
documented in [`validation.md`](validation.md).

## Registration receipt

Complete these fields only after the panel and hashes are frozen:

- Public commit: `PENDING`
- Signed Git tag: `PENDING`
- OSF Open-Ended Registration: `PENDING`
- Registration time: `PENDING`
- First allowed scored run: strictly after all four fields above are public
