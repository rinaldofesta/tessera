"""The ONLY inspect_ai-importing module in the report package.

Normalizes a public EvalLog into pure RunHeader + ProbeEpoch records. Reads only stable
top-level fields (no `_log` internals).
"""

from __future__ import annotations

from inspect_ai.log import EvalLog

from tessera.report.models import ProbeEpoch, ReportError, RunHeader

_AXIS_KEYS = {"passed", "accuracy_ok", "provenance_ok", "refusal_ok"}


def _select_score(scores: dict):
    """Pick the reliability score: the one whose metadata carries our axis keys.

    Robust to the scorer's function name (deterministic_/llm_reliability_scorer); falls
    back to the sole entry when there is exactly one.
    """
    if not scores:
        return None
    for s in scores.values():
        if s.metadata and _AXIS_KEYS.issubset(s.metadata.keys()):
            return s
    if len(scores) == 1:
        return next(iter(scores.values()))
    return None


def _grader_id(model_roles) -> str | None:
    if not model_roles:
        return None
    gr = model_roles.get("grader")
    if gr is None:
        return None
    return getattr(gr, "model", None) or str(gr)


def eval_log_to_records(log: EvalLog) -> tuple[RunHeader, list[ProbeEpoch]]:
    if not log.samples:
        raise ReportError("log contains no samples")

    spec = log.eval
    args = spec.task_args or {}
    engine = str(args.get("judge", "deterministic"))

    records: list[ProbeEpoch] = []
    scorer_version: str | None = None
    for s in log.samples:
        score = _select_score(s.scores or {})
        if score is None or not score.metadata or not _AXIS_KEYS.issubset(score.metadata.keys()):
            raise ReportError("not a Tessera reliability log (no axis metadata in scores)")
        m = s.metadata or {}
        sm = score.metadata
        scorer_version = scorer_version or sm.get("scorer_version")
        fmt = sm.get("answer_format_ok")
        records.append(ProbeEpoch(
            probe_id=str(s.id),
            epoch=int(s.epoch),
            conflict_type=str(m.get("conflict_type", "")),
            expected_behavior=str(m.get("expected_behavior", "")),
            passed=bool(sm["passed"]),
            accuracy_ok=bool(sm["accuracy_ok"]),
            provenance_ok=bool(sm["provenance_ok"]),
            refusal_ok=bool(sm["refusal_ok"]),
            consulted=tuple(sm.get("consulted", []) or []),
            expected_sources=tuple(m.get("expected_sources", []) or []),
            question=(s.input if isinstance(s.input, str) else str(s.input)),
            answer=str(score.answer or ""),
            expected_answer=m.get("expected_answer"),
            answer_format_ok=(bool(fmt) if fmt is not None else None),
        ))

    header = RunHeader(
        model=str(spec.model),
        engine=engine,
        k=(spec.config.epochs or 1),
        created=str(spec.created),
        location=str(log.location),
        grader=(_grader_id(spec.model_roles) if engine == "llm" else None),
        org=(str(args["org"]) if "org" in args else None),
        scorer_version=(str(scorer_version) if scorer_version else None),
        inspect_ai_version=(spec.packages or {}).get("inspect_ai"),
    )
    return header, records
