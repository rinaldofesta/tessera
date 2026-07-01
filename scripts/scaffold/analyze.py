#!/usr/bin/env python3
"""Analyze the scaffold-intervention runs: per-type pass^k for B0 vs R1, the net-correct-
behaviour delta, and the paired McNemar tests over probe-instances — including the
refusal/answerable subset decomposition that ADR-0009 declares as the test of H1₂ (the
p-values published in docs/scaffold.md and docs/report.md §6 are reproduced here).

Reuses the repo's own extraction (log_adapter, aggregate) so pass^k semantics match the
leaderboard exactly, and the tested stats module (report.stats) for the exact test.
Breadth seeds are allowlisted (--seeds, default the published 0-4) so a holdout run
left under logs/scaffold/ can never silently pool into the breadth tables."""
from __future__ import annotations

import argparse
import glob
import os
from collections import defaultdict

from inspect_ai.log import read_eval_log

from tessera.report.aggregate import aggregate_by, overall_pass_k_rate, reduce_by_probe
from tessera.report.leaderboard import _pct as fmt  # the leaderboard's rate formatter
from tessera.report.log_adapter import eval_log_to_records
from tessera.report.models import CANONICAL_ORDER, ReportError
from tessera.report.stats import exact_mcnemar_p, format_p, mcnemar_counts

ARMS = ("baseline", "refusal_aware")
# H1₂'s two disjoint subsets (ADR-0009 §3). The split is by expected behavior, which
# coincides with conflict-type membership: refuse = unresolvable+void, answer = none+resolvable.
SUBSETS = (("refusal (unr+void)", "refuse"), ("answerable (none+res)", "answer"))


def load(patterns, seeds_allowed):
    """(model, seed, scaffold) -> {probe_id: ProbeReliability}; skips and reports bad logs."""
    runs, headers, seen = {}, {}, set()
    excluded = set()
    for pattern in patterns:
        for path in sorted(glob.glob(pattern, recursive=True)):
            if path in seen:
                continue
            seen.add(path)
            log = read_eval_log(path)
            if log.status != "success":
                print(f"!! skipping {path}: status={log.status}")
                continue
            try:
                header, records = eval_log_to_records(log)
            except ReportError as e:
                print(f"!! skipping {path}: {e}")
                continue
            if seeds_allowed is not None and header.seed not in seeds_allowed:
                excluded.add(header.seed)
                continue
            key = (header.model, header.seed, header.scaffold)
            if key in runs:
                print(f"!! duplicate run for {key}: {path} shadows {headers[key][1]}")
            runs[key] = {p.probe_id: p for p in reduce_by_probe(records)}
            headers[key] = (header, path)
    if excluded:
        print(f"!! excluded seeds {sorted(excluded)} — outside --seeds; the holdout is "
              "reported separately (docs/scaffold.md), never pooled into the breadth tables")
    return runs, headers


def require_comparable(headers):
    """The executable comparability rule (mirrors leaderboard._require_uniform): one
    analysis = one protocol. A stray -T k=1 / judge=llm / other-org log aborts loudly
    instead of silently entering the McNemar contingency."""
    for field in ("k", "org", "scorer_version", "engine"):
        values = {getattr(h, field) for h, _ in headers.values()}
        if len(values) > 1:
            detail = "\n".join(f"  {field}={getattr(h, field)!r}  {p}"
                               for h, p in headers.values())
            raise SystemExit(f"runs are not comparable: {field} differs across logs\n{detail}")


def per_type(probes):
    cats = {c.key: c.pass_k_rate for c in aggregate_by(list(probes.values()))}
    return cats, overall_pass_k_rate(list(probes.values()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("globs", nargs="*",
                    help="eval-log globs (default: <repo>/logs/scaffold/s*/*.eval)")
    ap.add_argument("--seeds", default="0,1,2,3,4",
                    help="breadth seeds to pool (default: the published 0-4); "
                         "'all' disables the filter")
    args = ap.parse_args(argv)

    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    patterns = args.globs or [os.path.join(repo, "logs/scaffold/s*/*.eval")]
    seeds_allowed = None if args.seeds == "all" else {int(s) for s in args.seeds.split(",")}

    runs, headers = load(patterns, seeds_allowed)
    if not runs:
        raise SystemExit(f"no runs loaded from {patterns} — run.sh writes one dir per run "
                         "matching logs/scaffold/s*/; point globs there")
    require_comparable(headers)

    models = sorted({m for (m, s, sc) in runs})
    seeds = sorted({s for (m, s, sc) in runs})
    print(f"loaded {len(runs)} runs · models={models} · seeds={seeds}\n")

    # Pair the arms once; every section below reads this, so the per-seed table, the
    # pooled tables, and the McNemar lines all describe the SAME sample set.
    paired = defaultdict(dict)  # model -> seed -> (b0_probes, r1_probes)
    for m in models:
        for s in seeds:
            b0 = runs.get((m, s, "baseline"))
            r1 = runs.get((m, s, "refusal_aware"))
            if b0 and r1:
                paired[m][s] = (b0, r1)
            elif b0 or r1:
                have = "baseline" if b0 else "refusal_aware"
                print(f"!! {m} seed {s}: only the {have} arm — excluded from ALL tables")

    print("=== Per model × seed: net-correct-behaviour (overall pass^k) and unresolvable column ===")
    print(f"{'model':28} {'seed':>4} {'B0 net':>7} {'R1 net':>7} {'Δnet':>6} "
          f"{'B0 unr':>7} {'R1 unr':>7} {'b(hurt)':>7} {'c(help)':>7}")
    for m in models:
        for s, (b0, r1) in sorted(paired[m].items()):
            c0, net0 = per_type(b0)
            c1, net1 = per_type(r1)
            b, c, dropped = mcnemar_counts({p: pr.pass_k for p, pr in b0.items()},
                                           {p: pr.pass_k for p, pr in r1.items()})
            if dropped:
                print(f"!! {m} seed {s}: probes present in only one arm, unpaired: {dropped}")
            print(f"{m:28} {s:>4} {fmt(net0):>7} {fmt(net1):>7} "
                  f"{(net1-net0)*100:>+5.1f} {fmt(c0.get('unresolvable')):>7} "
                  f"{fmt(c1.get('unresolvable')):>7} {b:>7} {c:>7}")

    print("\n=== Pooled across paired seeds: per-type pass^k, overall + H1₂ subset McNemar ===")
    for m in models:
        if not paired[m]:
            continue
        pooled = {arm: {} for arm in ARMS}
        for s, (b0, r1) in paired[m].items():
            for arm, probes in (("baseline", b0), ("refusal_aware", r1)):
                for pid, pr in probes.items():
                    pooled[arm][(s, pid)] = pr
        for arm, tag in (("baseline", "B0"), ("refusal_aware", "R1")):
            cats, net = per_type(pooled[arm])
            print(f"{m:28} {tag} net={fmt(net):>7} | " +
                  " ".join(f"{k}={fmt(cats.get(k)):>6}" for k in CANONICAL_ORDER) +
                  f"  (n={len(pooled[arm])} probe-instances, seeds {sorted(paired[m])})")
        b0_pass = {k: pr.pass_k for k, pr in pooled["baseline"].items()}
        r1_pass = {k: pr.pass_k for k, pr in pooled["refusal_aware"].items()}
        b, c, dropped = mcnemar_counts(b0_pass, r1_pass)
        note = f"  ({len(dropped)} unpaired probe-instances dropped)" if dropped else ""
        print(f"{'':28} overall: b(R1 hurt)={b}  c(R1 helped)={c}  "
              f"exact two-sided p={format_p(exact_mcnemar_p(b, c))}{note}")
        for label, behavior in SUBSETS:
            fb0 = {k: pr.pass_k for k, pr in pooled["baseline"].items()
                   if pr.expected_behavior == behavior}
            fr1 = {k: pr.pass_k for k, pr in pooled["refusal_aware"].items()
                   if pr.expected_behavior == behavior}
            b, c, _ = mcnemar_counts(fb0, fr1)
            print(f"{'':28} {label}: b(R1 hurt)={b}  c(R1 helped)={c}  "
                  f"exact two-sided p={format_p(exact_mcnemar_p(b, c))}")
        print()


if __name__ == "__main__":
    main()
