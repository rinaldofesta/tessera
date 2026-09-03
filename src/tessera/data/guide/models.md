# Connecting a model

Cloud providers need a key. Ollama needs only a running daemon. MLX and other OpenAI-compatible servers need their base URL.

## Cloud providers

Run `tessera connect anthropic` and paste the key at the hidden prompt. For scripts, pass the key through standard input with `--key-stdin`:

```console
printf '%s' "$ANTHROPIC_API_KEY" | tessera connect anthropic --key-stdin
```

The Run form asks for a key inline when one is missing. Tessera saves the key in `~/.tessera/.env` with mode `0600` and never prints it.

## Ollama

Start the local daemon:

```console
ollama serve
```

Use the model id `ollama/<tag>`. There is no connect step when Ollama uses its default local address. If Ollama runs elsewhere, set its URL with `tessera connect ollama --base-url http://host:11434/v1`.

## MLX, vLLM and other OpenAI-compatible servers

Start an MLX server, then connect Tessera to it:

```console
mlx_lm.server --model <hf-repo> --port 8090
tessera connect mlx --base-url http://localhost:8090/v1
```

Use the model id `openai-api/mlx/<hf-repo>`. Tessera also writes the placeholder `MLX_API_KEY=local` that inspect_ai requires. Local servers ignore its value. vLLM and other OpenAI-compatible servers use the same connection. Add `--test MODEL` to the connect command to probe the server.
