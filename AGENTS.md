# Using Evalogy as a coding agent

Evalogy measures whether an agent answers questions over disagreeing company sources accurately, with traceable evidence, and with honest refusal when no answer is justified. It repeats each question because an answer that works only sometimes is not reliable.

## Commands and JSON contracts

- `evalogy run --model MODEL --dry-run --json` plans without model calls and returns a plan with `ready`, `blockers`, `request`, `suite`, and `scorer_version`.
- `evalogy run --model MODEL --json` returns the run envelope: `ok`, `id`, `status`, `request`, `verdict`, `gate`, `report`, `receipt`, `diagnostics`, `paths`, and `error`.
- `evalogy report REF --json` returns a stored run envelope; for a raw `.eval` log it returns `{"ok": true, "report": ..., "verdict": ...}`.
- `evalogy history --json` returns `{"ok": true, "runs": [...]}`.
- `evalogy catalog [SECTION] --json` returns `{"ok": true, ...requested catalog data..., "defaults": ...}`.
- `evalogy connect PROVIDER --key-stdin --json` returns `{"ok": true, "provider": ..., "probe": ...}`.
- `evalogy compare A B --json` returns `{"ok": true, "comparable": ..., ...paired results...}`.
- `evalogy ui --check --json` returns `{"ok": ..., "api": "ok", "ui_bundle": ..., "home": ..., "env_file": ..., "env_file_present": ...}`. `ok`/`ui_bundle` reflect whether the packaged UI bundle is present; a missing bundle is `"ok": false` with `"ui_bundle": null` and exits `4`, without the `{"error": ...}` envelope below.
- `evalogy guide [TOPIC] --json` returns either `{"ok": true, "topic": ..., "text": ...}` or `{"ok": true, "topics": [...]}` with `--list`.
- `evalogy init NAME --json` returns `{"ok": true, "path": ..., "name": ...}`.
- `evalogy validate REF --json` returns `{"ok": ..., "issues": [...], "questions": ..., "claims": ...}`.

Every handled error under `--json` is `{"ok": false, "error": {"code": ..., "message": ..., "fix": ...}}`, except validation, which keeps its validation result envelope.

Exit codes are stable:

- `0`: the command completed. A completed evaluation may still be unreliable.
- `1`: a gate you explicitly requested failed, such as `--min-pass-k` or `--require-comparable`. It does not mean an ungated run was unreliable, and unreliability alone does not produce exit 1.
- `2`: a required provider is not connected.
- `3`: the command or suite specification is invalid.
- `4`: Evalogy hit a runtime failure.

`evalogy leaderboard render/extract/verify` are manifest tooling, not eval commands — they never call a model or touch a provider, so they keep their own narrower contract (`0` on success, `2` on an unreadable manifest/log or a verification mismatch) instead of this table.

## State and credentials

State lives under `~/.evalogy`. Set `EVALOGY_HOME` to move all state, or `EVALOGY_ENV_FILE` to move only the credential file.

Connect a key through standard input so it never appears in argv:

```sh
printf '%s' "$KEY" | evalogy connect anthropic --key-stdin
```

Ollama needs no connect step; use `ollama/<tag>`. For MLX, vLLM, and other OpenAI-compatible servers, run `evalogy connect mlx --base-url URL` and use `openai-api/mlx/<repo>`. Run `evalogy guide models` for the long form.

Never echo keys. Do not put a key in a command argument, file under version control, log, report, or agent response.

## Working rules

- Start with `evalogy run --model MODEL --dry-run --json`; connect only the provider named by a blocker.
- Use `evalogy validate NAME` before running an authored suite.
- Read the verdict sentence first, then inspect `pass^k`, `mean`, categories, and the failure appendix.
- Do not run live evaluations in CI unless the required key is explicitly available; dry-runs, validation, reports, and catalog checks are key-free.
- Do not hand-edit `openapi.json` or `docs/leaderboard.md`; use the repository generators.

For detailed procedures, read `skills/evalogy-run/SKILL.md`, `skills/evalogy-author/SKILL.md`, and `skills/evalogy-publish/SKILL.md`.
