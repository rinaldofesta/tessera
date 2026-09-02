# Related work

Where Tessera sits among the MCP benchmarks, and what it does not try to do.

The MCP benchmark field is no longer empty. [MCP-AgentBench](https://doi.org/10.1609/aaai.v40i37.40347), [MCP-Universe](https://arxiv.org/abs/2508.14704), [MCP-Bench](https://arxiv.org/abs/2508.20453), [MCPMark](https://arxiv.org/abs/2509.24002) and [MCP-Atlas](https://arxiv.org/abs/2602.00933) measure broad task completion over real MCP servers. [MCPEval](https://aclanthology.org/2025.emnlp-demos.27/) and [DynamicMCPBench](https://arxiv.org/abs/2607.20531) automate task generation. [Toloka](https://toloka.ai/blog/the-importance-of-mcp-evaluations-in-agentic-ai/) sells managed environments that mirror production systems and uses repeated trials.

Tessera's target is narrower: fragmented knowledge. Controlled contradictions and gaps across silos, per-field provenance read from the agent's tool traffic, epistemic refusal, the cost of false refusal, and a generator a builder can point at an organisation's own eval. It does not compete on server breadth or task count.

Method, limits and measured results: [`report.md`](report.md). The next validation study is specified before the run in [`validation-preregistration.md`](validation-preregistration.md).
