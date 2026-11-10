---
tags: [research, models, retrieval, on-prem]
date: 2026-11-10
status: partly unverified
---

# On-prem open models and retrieval

Research agent report, 2026-11-10. Much of it comes from blogs; primary sources are marked. Related: [[02-ai-threats-and-controls]], [[04-token-usage-and-agent-teams]].

## Models that fit 8 GB VRAM

- Qwen3.5-9B: Apache-2.0, 262K context, tool calling. (primary) https://huggingface.co/Qwen/Qwen3.5-9B
- Gemma 4 E4B: 128K context, licence tag Apache 2.0; legal should read the actual licence text. (primary) https://huggingface.co/google/gemma-4-E4B-it
- Phi-4-mini (MIT), Qwen3-8B (Apache-2.0), Granite 4.1 8B (listed as Apache-2.0, specs unverified). https://pinggy.io/amp/blog/small_llms_that_fit_in_8gb_memory/
- Apache-2.0 and MIT are the licences a bank's legal team accepts most easily.
- Structured output is enforced by the server, not the model.

## Why banks want on-prem

- Bank of England and FCA 2026 AI survey (26 October 2026): third-party systems are 39% of all AI systems and 53% of high-materiality ones; the top three cloud providers hold 79% of reported relationships. Secondary summary: https://www.resultsense.com/news/2026-10-27-boe-fca-ai-survey-2026-agents-third-parties/ Primary: https://www.bankofengland.co.uk/report/2026/artificial-intelligence-in-uk-financial-services-2026
- April 2026 PRA letter: firms using third-party AI models should assess concentration risk. (secondary) https://www.resultsense.com/insights/2026-10-28-uk-financial-services-ai-agents-autonomy-concentration/
- HM Treasury designated AWS, Google Cloud, Microsoft and Oracle as critical third parties on 13 July 2026 (same source).
- No bank or regulator quote found on cost predictability or auditability.

## Retrieval

- Standard small-corpus pattern: SQLite FTS5 with BM25, optionally plus sqlite-vec, fused by reciprocal rank fusion. https://dev.to/soytuber/building-a-hybrid-rag-in-200-lines-sqlite-fts5-sqlite-vec-rrf-38h1
- BM25 is a strong baseline for legal-style retrieval (Rosa et al., COLIEE 2021, via secondary summary). https://dev.to/gabrielanhaia/rag-without-embeddings-when-bm25-beats-your-020-per-1k-vector-index-2140
- Dense retrieval can miss exact identifiers such as clause numbers (vendor claim). https://www.vaquill.ai/engineering/hybrid-retrieval-and-the-exact-identifier-problem
- Latency figures found were weak. Measure it ourselves.

## Grounded output

- Ollama: pass a JSON schema in the `format` field. (primary) https://docs.ollama.com/capabilities/structured-outputs
- llama.cpp: GBNF grammars. (primary) https://raw.github.com/ggerganov/llama.cpp/master/./grammars/README.md
- Quote-then-answer with a verbatim substring check is standard practice, but no source was found.

## Recommended stack

- Model: Qwen3.5-9B at Q4_K_M, Gemma 4 E4B as fallback.
- Server: Ollama, for the simplest Windows install and schema-enforced JSON.
- Retrieval: SQLite FTS5 with BM25 first. Add vectors only if measured recall needs it.
