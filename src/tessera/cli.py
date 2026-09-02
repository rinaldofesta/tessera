"""The single Tessera command-line interface."""

from __future__ import annotations

import json
import os
import sys
from enum import Enum
from functools import wraps
from pathlib import Path

import click
import typer
from dotenv import load_dotenv
from typer.core import TyperGroup

from tessera import __version__, paths, providers
from tessera import catalog as catalog_module
from tessera.api.providers import FIELD_API_KEY, PROVIDERS
from tessera.api.scrub import scrub_error
from tessera.errors import (
    ExitCode,
    GateFailed,
    NotConnectedError,
    SpecError,
    TesseraError,
)
from tessera.report.compare import compare_reports
from tessera.report.render import render_markdown
from tessera.report.serialize import report_to_dict
from tessera.runner import execute, plan, run_result_payload
from tessera.store import RunRecord, RunStore
from tessera.verdict import verdict_of


class _NoArgsHelpGroup(TyperGroup):
    """Click treats implicit help as a usage error; Tessera treats it as success."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            click.echo(ctx.get_help())
            ctx.exit()
        return super().parse_args(ctx, args)


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode=None,
    cls=_NoArgsHelpGroup,
)


class EngineOption(str, Enum):
    deterministic = "deterministic"
    llm = "llm"


class CatalogSection(str, Enum):
    suites = "suites"
    models = "models"
    scorers = "scorers"
    providers = "providers"


class Context:
    """Paths and storage resolved together from the current Tessera environment."""

    def __init__(self) -> None:
        self.home = paths.home()
        self.store = RunStore(self.home)
        self.suites_dir = paths.suites_dir()
        self.env_file = paths.env_file()
        load_dotenv(self.env_file, interpolate=False, override=False)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _error_payload(exc: TesseraError) -> dict:
    return {
        "ok": False,
        "error": {
            "code": ExitCode(exc.exit_code).name.lower(),
            "message": str(exc),
            "fix": getattr(exc, "fix", None),
        },
    }


def _guard(command):
    """Give every command the same redacted errors, JSON envelope, and exit codes."""

    @wraps(command)
    def guarded(*args, **kwargs):
        json_output = bool(kwargs.get("json_output", False))
        try:
            return command(*args, **kwargs)
        except KeyboardInterrupt:
            raise typer.Exit(code=130) from None
        except typer.Exit:
            raise
        except TesseraError as exc:
            if json_output:
                _print_json(_error_payload(exc))
            else:
                typer.echo(f"error: {exc}", err=True)
                if fix := getattr(exc, "fix", None):
                    typer.echo(f"fix: {fix}", err=True)
            raise typer.Exit(code=int(exc.exit_code)) from None
        except Exception as exc:  # noqa: BLE001 — this is the no-traceback CLI boundary
            error = TesseraError(scrub_error(f"{type(exc).__name__}: {exc}"))
            if json_output:
                _print_json(_error_payload(error))
            else:
                typer.echo(f"error: {error}", err=True)
            raise typer.Exit(code=int(error.exit_code)) from None

    return guarded


def _record_for_ref(context: Context, ref: str) -> RunRecord:
    if ref != "latest":
        return context.store.get(ref)
    for record in context.store.list(include_archived=True):
        if record.data.get("source") != "bundled":
            return record
    raise SpecError("there are no runs yet")


def _raise_plan_error(blockers: list[dict]) -> None:
    not_connected = next(
        (blocker for blocker in blockers if blocker["code"] == "not_connected"),
        None,
    )
    error_type = NotConnectedError if not_connected else SpecError
    error = error_type("; ".join(blocker["message"] for blocker in blockers))
    if not_connected and not_connected.get("fix"):
        error.fix = not_connected["fix"]
    raise error


def _raise_gate_failed(json_output: bool, message: str) -> None:
    """The result was already printed; the exit code alone carries the gate for JSON."""
    if json_output:
        raise typer.Exit(code=int(ExitCode.GATE_FAILED))
    raise GateFailed(message)


def _print_plan(payload: dict) -> None:
    typer.echo(f"ready: {'yes' if payload['ready'] else 'no'}")
    for blocker in payload["blockers"]:
        suffix = f" · fix: {blocker['fix']}" if blocker.get("fix") else ""
        typer.echo(f"blocker: {blocker['message']}{suffix}")
    request = payload["request"]
    suite = payload["suite"]
    typer.echo(f"suite: {suite['name'] if suite else request['suite']}")
    typer.echo(f"model: {request['model']}")
    typer.echo(f"engine: {request['engine']}")
    if request.get("grader"):
        typer.echo(f"grader: {request['grader']}")
    typer.echo(f"k: {request['k']}")
    typer.echo(f"scaffold: {request['scaffold']}")
    typer.echo(f"seed: {request['seed']}")
    typer.echo(f"scorer: {payload['scorer_version']}")


def _print_run_result(payload: dict) -> None:
    verdict = payload["verdict"]
    request = payload["request"]
    typer.echo(verdict["sentence"])
    typer.echo(
        f"pass^{request['k']} {verdict['pass_k_rate']:.0%} · "
        f"mean {verdict['mean_rate']:.0%}"
    )
    typer.echo(f"saved {payload['paths']['dir']}")
    typer.echo(f"next: tessera report {payload['id']}")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"tessera {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        is_eager=True,
        callback=_version_callback,
        help="Show the Tessera version and exit.",
    ),
) -> None:
    pass


@app.command()
@_guard
def run(
    model: str = typer.Option(..., "--model"),
    suite: str = typer.Option("starter", "--suite"),
    engine: EngineOption = typer.Option(EngineOption.deterministic, "--engine"),
    grader: str | None = typer.Option(None, "--grader"),
    k: int = typer.Option(3, "--k"),
    scaffold: str = typer.Option("baseline", "--scaffold"),
    seed: int = typer.Option(0, "--seed"),
    min_pass_k: float | None = typer.Option(None, "--min-pass-k"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Plan and execute a reliability evaluation."""
    if min_pass_k is not None and not 0 <= min_pass_k <= 1:
        raise SpecError("--min-pass-k must be between 0 and 1")
    context = Context()
    spec = {
        "suite": suite,
        "model": model,
        "engine": engine.value,
        "grader": grader,
        "k": k,
        "scaffold": scaffold,
        "seed": seed,
    }
    run_plan = plan(spec, env=os.environ, suites_dir=context.suites_dir)
    if dry_run:
        if json_output:
            _print_json(run_plan)
        else:
            _print_plan(run_plan)
        return

    if not run_plan["ready"]:
        _raise_plan_error(run_plan["blockers"])

    request = run_plan["request"]
    record = context.store.create(request)
    typer.echo(
        f"running {request['suite']} on {request['model']} — {request['k']} repeats, "
        "this can take a few minutes…",
        err=True,
    )
    executed_payload = execute(
        record,
        request,
        store=context.store,
        suites_dir=context.suites_dir,
        env=os.environ,
    )
    # execute() already built and returned the payload for this record; only rebuild it
    # (a second store.get() + report/receipt read) when a --min-pass-k gate needs to be
    # folded in, since execute()'s own payload never carries one.
    payload = (
        run_result_payload(context.store.get(record.id), min_pass_k=min_pass_k)
        if min_pass_k is not None
        else executed_payload
    )
    if payload["status"] != "completed":
        if json_output:  # the payload is the error report; exit code says the rest
            _print_json(payload)
            raise typer.Exit(code=int(ExitCode.RUNTIME_ERROR))
        raise TesseraError(payload["error"] or "run failed")

    if json_output:
        _print_json(payload)
    else:
        _print_run_result(payload)

    gate = payload.get("gate")
    if gate is not None and not gate["passed"]:
        verdict = payload["verdict"]
        _raise_gate_failed(
            json_output,
            f"pass^{request['k']} {verdict['pass_k_rate']:.0%} is below "
            f"--min-pass-k {min_pass_k:.0%}",
        )


@app.command()
@_guard
def report(
    ref: str = typer.Argument("latest", metavar="REF"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Render a stored run or an Inspect .eval log."""
    context = Context()
    log_path = Path(ref)
    if ref.endswith(".eval") and log_path.is_file():
        from tessera.report.log_adapter import read_log  # inspect_ai only for raw logs

        report_data = report_to_dict(read_log(log_path))
        if json_output:
            _print_json({
                "ok": True,
                "report": report_data,
                "verdict": verdict_of(report_data),
            })
        else:
            typer.echo(render_markdown(report_data), nl=False)
        return

    record = _record_for_ref(context, ref)
    if json_output:
        _print_json(run_result_payload(record))
        return
    markdown = record.markdown()
    if markdown is None and (report_data := record.report()) is not None:
        markdown = render_markdown(report_data)
    if markdown is None:
        raise SpecError(f"run {record.id} has no report")
    typer.echo(markdown, nl=False)


def _print_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    # One tuple argument, not `max(a, *bs)`: with zero rows `*bs` unpacks to nothing and
    # `max(a)` treats the lone int as an iterable to exhaust, raising TypeError instead
    # of just returning `a`.
    widths = [
        max((len(headers[index]), *(len(row[index]) for row in rows)))
        for index in range(len(headers))
    ]
    typer.echo("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(headers)))
    for row in rows:
        typer.echo("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))


@app.command()
@_guard
def history(
    archived: bool = typer.Option(False, "--archived"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List saved and bundled runs."""
    context = Context()
    payloads = [
        run_result_payload(record, include_report=False)
        for record in context.store.list(include_archived=archived)
    ]
    if json_output:
        _print_json({"ok": True, "runs": payloads})
        return
    rows = []
    for payload in payloads:
        verdict = payload["verdict"]
        when = payload["created_at"][:16]
        if payload["source"] == "bundled":
            when += " (bundled)"
        rows.append((
            payload["id"],
            payload["request"]["model"],
            payload["request"]["suite"],
            str(payload["request"]["k"]),
            verdict["label"] if verdict else payload["status"],
            f"{verdict['pass_k_rate']:.0%}" if verdict else "—",
            when,
        ))
    _print_table(("ID", "MODEL", "SUITE", "K", "VERDICT", "PASS^K", "WHEN"), rows)


@app.command()
@_guard
def archive(
    ref: str = typer.Argument(..., metavar="REF"),
    restore: bool = typer.Option(False, "--restore"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Archive or restore a home run."""
    context = Context()
    record = _record_for_ref(context, ref)
    record = context.store.set_archived(record.id, not restore)
    if json_output:
        _print_json(run_result_payload(record, include_report=False))
    else:
        action = "restored" if restore else "archived"
        typer.echo(f"{action} {record.id}")


@app.command("import")
@_guard
def import_log(
    log: str = typer.Argument(..., metavar="LOG"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Import an existing Inspect .eval log into history."""
    context = Context()
    record = context.store.import_log(Path(log))
    payload = run_result_payload(record)
    if json_output:
        _print_json(payload)
    else:
        typer.echo(payload["verdict"]["sentence"])
        typer.echo(f"imported as {record.id}")


def _catalog_human(catalog: dict, section: str | None) -> None:
    selected = [section] if section else ["suites", "models", "scorers", "providers"]
    for index, name in enumerate(selected):
        if index:
            typer.echo("")
        typer.echo(name)
        if name == "suites":
            for row in catalog["suites"]:
                typer.echo(
                    f"{row['name']}  {row['label']}  {row['questions']}  {row['kind']}"
                )
        elif name == "models":
            for row in catalog["models"]:
                state = "connected" if row["connected"] else "not connected"
                typer.echo(f"{row['id']}  {row['provider']}  {state}")
        elif name == "providers":
            for row in catalog["providers"]:
                state = "connected" if row["connected"] else "not connected"
                fields = ",".join(row["fields"])
                typer.echo(f"{row['id']}  {row['label']}  {state}  {fields}")
        elif name == "scorers":
            for row in catalog["scorers"]:
                typer.echo(f"{row['engine']}  {row['version']}")
    defaults = catalog["defaults"]
    typer.echo("")
    typer.echo(
        "defaults: "
        f"suite={defaults['suite']}  engine={defaults['engine']}  k={defaults['k']}  "
        f"scaffold={defaults['scaffold']}  seed={defaults['seed']}"
    )


def _show_catalog(section: str | None, json_output: bool, context: Context) -> None:
    payload = catalog_module.build_catalog(env=os.environ, suites_dir=context.suites_dir)
    if json_output:
        # Scoped like the human branch below: a specific section (e.g. "providers" from
        # `catalog providers --json` or the no-provider `connect --json`) must not still
        # hand back the full suites/models/scorers/providers catalog.
        body = {section: payload[section]} if section else {
            key: payload[key] for key in ("suites", "models", "scorers", "providers")
        }
        _print_json({"ok": True, **body, "defaults": payload["defaults"]})
    else:
        _catalog_human(payload, section)


@app.command()
@_guard
def catalog(
    section: CatalogSection | None = typer.Argument(None),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List suites, models, scorers, and provider connection state."""
    _show_catalog(section.value if section else None, json_output, Context())


def _reject_control_characters(value: str) -> None:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise SpecError("value must not contain control characters")


def _stdin_secret() -> str:
    return sys.stdin.readline().strip()


@app.command()
@_guard
def connect(
    provider: str | None = typer.Argument(None, metavar="PROVIDER"),
    key_stdin: bool = typer.Option(False, "--key-stdin"),
    base_url: str | None = typer.Option(None, "--base-url"),
    test_model: str | None = typer.Option(None, "--test", metavar="MODEL"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Save a provider connection without putting credentials in argv."""
    context = Context()
    if provider is None:
        _show_catalog("providers", json_output, context)
        return

    provider_spec = PROVIDERS.get(provider)
    if provider_spec is None:
        raise SpecError(f"unknown provider: {provider}")
    if not provider_spec.needs_credentials:
        raise SpecError(f"provider '{provider}' does not use a stored credential")
    field_ids = {field.id for field in provider_spec.fields}
    if base_url is not None and "base_url" not in field_ids:
        raise SpecError("provider does not accept: base_url")

    api_key = None
    if FIELD_API_KEY in field_ids:
        api_key = _stdin_secret() if key_stdin else typer.prompt("API key", hide_input=True)
        _reject_control_characters(api_key)

    # providers.connect() only calls paths.ensure_home() (which chmods the home
    # directory 0700) down its `env_file is None` branch; passing an explicit env_file
    # — as every CLI call does — skips it, so on a fresh install `connect` as the first
    # command would otherwise leave ~/.tessera created at the process umask instead of
    # the 0700 every other code path treats as this directory's invariant.
    paths.ensure_home()
    provider_row = providers.connect(
        provider,
        api_key=api_key,
        base_url=base_url,
        env_file=context.env_file,
        invalidate=lambda: None,
    )
    probe_result = providers.probe(test_model) if test_model else None
    if json_output:
        _print_json({"ok": True, "provider": provider_row, "probe": probe_result})
        return

    typer.echo(f"✓ saved to {context.env_file} (0600)")
    if probe_result is not None:
        if probe_result["ok"]:
            typer.echo(
                f"✓ probe ok: {probe_result['model']} answered in "
                f"{probe_result['latency_seconds']:.1f} s"
            )
        else:
            typer.echo(f"✗ probe failed: {probe_result['error']}")


def _comparison_line(label: str, result: dict) -> str:
    return (
        f"{label}: A wins {result['a_wins']} · B wins {result['b_wins']} · "
        f"both pass {result['both_pass']} · both fail {result['both_fail']} · "
        f"McNemar p={result['p_value']:.3g}"
    )


@app.command()
@_guard
def compare(
    a: str = typer.Argument(..., metavar="A"),
    b: str = typer.Argument(..., metavar="B"),
    intervention: str = typer.Option("model", "--intervention"),
    require_comparable: bool = typer.Option(False, "--require-comparable"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Compare two runs with paired outcomes and compatibility checks."""
    context = Context()
    record_a = _record_for_ref(context, a)
    record_b = _record_for_ref(context, b)
    report_a = record_a.report()
    report_b = record_b.report()
    if report_a is None or report_b is None:
        raise SpecError("both runs must have completed reports")
    try:
        result = compare_reports(
            report_a,
            report_b,
            intervention=intervention,
            receipt_a=record_a.receipt(),
            receipt_b=record_b.receipt(),
        )
    except ValueError as exc:
        # compare_reports raises a bare ValueError for a bad --intervention; without this
        # it falls through _guard's catch-all as a RUNTIME_ERROR (exit 4) instead of the
        # SPEC_ERROR (exit 3) this CLI uses everywhere else for bad user input.
        raise SpecError(str(exc)) from None
    payload = {"ok": True, "comparable": result["compatible"], **result}
    if json_output:
        _print_json(payload)
    else:
        dimensions = (
            result["changed_dimensions"]
            if result["compatible"]
            else result["unexpected_dimensions"]
        )
        typer.echo(
            f"comparable: {'yes' if result['compatible'] else 'no'} "
            f"({', '.join(dimensions) if dimensions else 'none'})"
        )
        typer.echo(_comparison_line("overall", result["overall"]))
        for category in result["categories"]:
            typer.echo(_comparison_line(category["key"], category))

    if require_comparable and not result["compatible"]:
        detail = ", ".join(result["unexpected_dimensions"])
        _raise_gate_failed(json_output, f"the two runs are not comparable: {detail}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
