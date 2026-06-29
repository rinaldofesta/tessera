#!/usr/bin/env python3
"""Analyze the scaffold-intervention runs: per-type pass^k for B0 vs R1, the net-correct-
behaviour delta, and a paired McNemar test over probes. Reuses the repo's own extraction
so pass^k semantics match the leaderboard exactly."""
from __future__ import annotations

import glob
import sys
from collections import defaultdict

from inspect_ai.log import read_eval_log

from tessera.report.aggregate import aggregate_by, overall_pass_k_rate, reduce_by_probe
from tessera.report.log_adapter import eval_log_to_records

CANON = ["none", "resolvable", "unresolvable", "void"]


def load(globs):
    # key: (model, seed, scaffold) -> {probe_id: ProbeReliability}
    runs = {}
    for pattern in globs:
        for path in sorted(glob.glob(pattern, recursive=True)):
            log = read_eval_log(path)
            args = log.eval.task_args or {}
            scaffold = str(args.get("scaffold", "baseline"))
            seed = int(args.get("seed", 0))
            header, records = eval_log_to_records(log)
            probes = {p.probe_id: p for p in reduce_by_probe(records)}
            runs[(str(log.eval.model), seed, scaffold)] = probes
    return runs


def per_type(probes):
    cats = {c.key: c.pass_k_rate for c in aggregate_by(list(probes.values()))}
    return cats, overall_pass_k_rate(list(probes.values()))


def mcnemar_b_c(b0, r1):
    """Return (b, c): b = B0 pass & R1 fail (R1 hurt), c = B0 fail & R1 pass (R1 helped)."""
    b = c = 0
    for pid in set(b0) & set(r1):
        p0, p1 = b0[pid].pass_k, r1[pid].pass_k
        if p0 and not p1:
            b += 1
        elif p1 and not p0:
            c += 1
    return b, c


def fmt(x):
    return "—" if x is None else f"{x*100:.1f}".rstrip("0").rstrip(".") + "%"


def main():
    import os
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # breadth pool only: the holdout runs live one level deeper under logs/scaffold/holdout/
    # and are reported separately, so the single-level s*/ glob excludes them.
    globs = sys.argv[1:] or [os.path.join(repo, "logs/scaffold/s*/*.eval")]
    runs = load(globs)
    models = sorted({m for (m, s, sc) in runs})
    seeds = sorted({s for (m, s, sc) in runs})
    print(f"loaded {len(runs)} runs · models={models} · seeds={seeds}\n")

    # --- Per (model, seed): the headline contrast + McNemar ---
    print("=== Per model × seed: net-correct-behaviour (overall pass^k) and unresolvable column ===")
    print(f"{'model':28} {'seed':>4} {'B0 net':>7} {'R1 net':>7} {'Δnet':>6} "
          f"{'B0 unr':>7} {'R1 unr':>7} {'b(hurt)':>7} {'c(help)':>7}")
    agg_b = defaultdict(int); agg_c = defaultdict(int)  # per model, summed across seeds
    for m in models:
        for s in seeds:
            b0 = runs.get((m, s, "baseline")); r1 = runs.get((m, s, "refusal_aware"))
            if not b0 or not r1:
                continue
            c0, net0 = per_type(b0); c1, net1 = per_type(r1)
            b, c = mcnemar_b_c(b0, r1)
            agg_b[m] += b; agg_c[m] += c
            print(f"{m:28} {s:>4} {fmt(net0):>7} {fmt(net1):>7} "
                  f"{(net1-net0)*100:>+5.1f} {fmt(c0.get('unresolvable')):>7} "
                  f"{fmt(c1.get('unresolvable')):>7} {b:>7} {c:>7}")

    # --- Pooled per model across all seeds: per-type pass^k, both arms ---
    print("\n=== Pooled across seeds: per-conflict-type pass^k (B0 -> R1) ===")
    for m in models:
        for arm in ("baseline", "refusal_aware"):
            allp = {}
            for s in seeds:
                r = runs.get((m, s, arm))
                if r:
                    for pid, pr in r.items():
                        allp[(s, pid)] = pr
            if not allp:
                continue
            cats = {c.key: c.pass_k_rate for c in aggregate_by(list(allp.values()))}
            net = overall_pass_k_rate(list(allp.values()))
            tag = "B0" if arm == "baseline" else "R1"
            print(f"{m:28} {tag} net={fmt(net):>7} | " +
                  " ".join(f"{k}={fmt(cats.get(k)):>6}" for k in CANON) +
                  f"  (n={len(allp)} probe-instances)")
        # pooled McNemar
        B = agg_b[m]; C = agg_c[m]
        n = B + C
        # exact binomial two-sided p under H0: b==c (sign test on discordants)
        from math import comb
        if n:
            p = sum(comb(n, i) for i in range(0, min(B, C) + 1)) * 2 / (2 ** n)
            p = min(1.0, p)
        else:
            p = 1.0
        print(f"{'':28} McNemar discordants: b(R1 hurt)={B}  c(R1 helped)={C}  "
              f"exact two-sided p={p:.4f}\n")


if __name__ == "__main__":
    main()
