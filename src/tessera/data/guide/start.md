# What Tessera checks

You give an agent questions whose answers are spread across several company sources that sometimes disagree. Tessera plants conflicts it already knows about and asks every question several times. The agent is reliable only when it makes the right move every time.

## Your first run

```console
tessera report first-contact                                # a real scorecard, no key needed
tessera run --model anthropic/claude-sonnet-4-6 --dry-run   # what would run, and what is missing
tessera connect anthropic                                   # paste a key at the hidden prompt
tessera run --model anthropic/claude-sonnet-4-6             # the first verdict
tessera ui                                                  # the same, in the browser
```

## Reading the result

Right every time means the answer held up on every attempt.
Only sometimes means the agent can do it, but cannot be trusted to repeat it.
Never means the same question failed on every attempt.

The gap between `pass^k` and `mean` shows the gap between dependable behavior and occasional success.

Your connections, suites, runs, and reports live under `~/.tessera`.
