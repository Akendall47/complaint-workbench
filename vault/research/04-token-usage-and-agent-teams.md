---
tags: [research, tokens, agents]
date: 2026-11-10
status: mostly vendor claims
---

# Token usage and agent teams

Research agent report, 2026-11-10. Most figures are vendor or blog claims with no independent benchmark. Related: [[03-on-prem-models-and-retrieval]], [[05-ankura-solution-sets]].

## Tools

- Claude Code `/cost`, `/usage` and OpenTelemetry metrics (`claude_code.token.usage`, `claude_code.cost.usage`). https://code.claude.com/docs/en/costs
- ccusage reads local logs for Claude Code; `ccusage codex` is in beta. https://www.mintlify.com/ryoppippi/ccusage/family/codex
- RTK (command-output compression): the project claims 60-90% fewer tokens. No independent benchmark. https://themenonlab.blog/blog/rtk-cli-proxy-token-reduction-ai-agents
- Caveman (terse output): the author claims about 65% output-token saving. It adds input tokens per turn, so short sessions can come out negative. https://aiweekly.co/node/4762

## Where the data lives

- Claude Code: JSONL under `~/.claude/projects/<project>/`, with `message.usage` and `message.model` on assistant rows. Group by `message.id` to avoid double counting. The schema is undocumented. https://dev.to/newtorob/claude-code-and-codex-are-logging-your-token-usage-locally-here-is-how-to-read-it-580
- Codex: `~/.codex/sessions/` holds cumulative `token_count` events; subtract the previous total for per-turn usage.

## Routing and coordination

- Anthropic: agents use about 4x the tokens of chat, multi-agent systems about 15x. A lead model with cheaper subagents beat a single agent by 90.2% on an internal evaluation. (confirmed) https://www.anthropic.com/engineering/multi-agent-research-system
- RouteLLM: about 85% cost cut at 95% of GPT-4 quality on one benchmark, 35-45% on others (secondary). https://tianpan.co/blog/2025/11/03/llm-routing-model-cascades
- Cross-model review: a June 2026 preprint (not peer reviewed) tested 154 issues across 8 models from 5 providers. No single model exceeded about 64% recall, and 56.5% of defects were caught by only one model. https://zenodo.org/records/20519585
- Greptile (vendor): Codex and Claude each found more bugs in the other's code than in their own. https://www.greptile.com/blog/model-inversion

## Knowledge graphs and vaults

- CodeGraph (self-reported): 47-59% fewer tokens on average, 13% on a small repo. https://dev.to/hiroki-ii-ai/codegraph-the-open-source-tool-that-cut-my-ai-coding-token-usage-by-57-4a21
- Graphify has a `graphify benchmark` command that compares token use against reading every file. https://graphify.com/blog/reduce-token-usage-ai-coding-agents
- No evidence found for Obsidian vaults as agent memory.

## Enterprise governance of AI coding spend

- Controls in use: team and individual budgets, burn-rate alerts, per-team dashboards, model allow-lists, routing to a cheaper model at the limit. https://www.pointfive.co/blog/coding-agent-cost-management-discipline
- Caution from the same source: a cap with no quality gate moves the cost to the maintenance backlog.

## Measurement plan for this build

Per agent and per model tier, record:

1. Input, output, cache-read and cache-write tokens.
2. Estimated cost per model. Local model cost is zero plus electricity.
3. Turns and subagent calls.
4. Tasks completed, each with a pass or fail check.
5. Defects caught by cross-model review.
6. Wall-clock time per task.
7. Cost per accepted task.

See also: [[tf-idf-routing-classifier]], [[cheapest-tool-per-job]], [[token-cost]], [[cross-model-review]], [[closed-build-loop]]
