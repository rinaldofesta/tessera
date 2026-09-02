"""Explicit, short paid probe for model identity and tool-call capability."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable

from tessera.api.scrub import scrub_error


async def default_preflight_runner(model_id: str, require_tools: bool) -> dict:
    from inspect_ai.model import GenerateConfig, get_model
    from inspect_ai.tool import tool

    @tool(name="tessera_preflight")
    def preflight_tool():
        async def execute(value: str) -> str:
            """Echo a short value to prove that tool calling is available."""
            return value
        return execute

    model = get_model(model_id)
    started = time.perf_counter()
    if require_tools:
        output = await model.generate(
            "Call tessera_preflight once with value 'ready'. Do not answer in prose.",
            tools=[preflight_tool()], tool_choice="any",
            config=GenerateConfig(max_tokens=64, temperature=0), cache=False,
        )
    else:
        output = await model.generate(
            "Reply with the single word ready.",
            config=GenerateConfig(max_tokens=16, temperature=0), cache=False,
        )
    usage = output.usage
    tool_call = bool(getattr(output.message, "tool_calls", None))
    return {
        "model": model_id,
        "effective_model": output.model or getattr(output.message, "model", None),
        "tool_call": tool_call,
        "ok": not output.error and (tool_call or not require_tools),
        "error": scrub_error(output.error) if output.error else (
            "model answered without the required tool call" if require_tools and not tool_call else None
        ),
        "latency_seconds": max(0.0, time.perf_counter() - started),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "cached": False,
        "usage": {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
            "billed_cost": getattr(usage, "total_cost", None),
        },
    }


class PreflightCache:
    def __init__(self, runner: Callable[[str, bool], Awaitable[dict]] = default_preflight_runner,
                 ttl_seconds: float = 300) -> None:
        self.runner = runner
        self.ttl_seconds = ttl_seconds
        self._entries: dict[tuple[str, bool], tuple[float, dict]] = {}
        # A real threading.Lock, not asyncio.Lock: `run()` executes on the event loop
        # thread but provider-config routes that call `invalidate()` are sync `def`
        # routes FastAPI runs in a worker thread — an asyncio.Lock only ever
        # synchronizes coroutines on one loop and gives no cross-thread exclusion, so
        # invalidate() could race an in-flight cache write and be silently undone by
        # it. Scoped to just the dict access (not held across the network call) so
        # unrelated models' checks no longer serialize behind one another either.
        self._lock = threading.Lock()

    async def run(self, model: str, require_tools: bool, *, refresh: bool = False) -> dict:
        key = (model, require_tools)
        with self._lock:
            cached = self._entries.get(key)
            if not refresh and cached and time.monotonic() - cached[0] < self.ttl_seconds:
                return {**cached[1], "cached": True}
        try:
            result = await self.runner(model, require_tools)
        except Exception as exc:  # noqa: BLE001 — failure is useful capability evidence
            result = {
                "model": model, "effective_model": None, "tool_call": False,
                "ok": False, "error": scrub_error(f"{type(exc).__name__}: {exc}"),
                "latency_seconds": 0.0,
                "checked_at": datetime.now(timezone.utc).isoformat(), "cached": False,
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
                          "billed_cost": None},
            }
        with self._lock:
            self._entries[key] = (time.monotonic(), result)
        return result

    def invalidate(self) -> None:
        with self._lock:
            self._entries.clear()
