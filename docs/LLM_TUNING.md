# Serving the crew's LLM: what was measured, and what to set

Numbers below come from the author's box (one RTX PRO 6000 Blackwell, 96 GB) on 2026-10-30, reading vLLM's own metrics and startup log over about 7 hours of agent lanes. Anything marked *untested* is a recommendation, not a result.

| Measure | Value |
|---|---|
| KV cache at 46 GiB | 636,321 tokens (vLLM log), about 78 KB per token |
| KV usage while lanes ran | mean 26%, p95 82%, peak 99.9% at 25 running + 18 waiting |
| KV at the old 12 GiB pin | 94-100% with only 11-12 requests running, 3-5 waiting |
| Aggregate generation | mean 535 tok/s, peak 1,391 tok/s |
| Prefix cache hit rate | 62% (36.2M of 58.7M prompt tokens) |
| MTP speculative decoding | 81% of drafted tokens accepted, 3.2 of 4 per draft |
| Preemptions | 110 in 11,010 requests (1%) |
| Time to first token | mean 1.0 s |

## Findings
1. **Do not shrink KV while agents run.** 12 GiB starves at 12 lanes. KV is the trade between VRAM for renders and agent concurrency; `llm_tiers.kv_budget(tokens)` does the sum. For renders, use vLLM sleep level 1, which released the card and woke cleanly in every render window so far.
2. **MTP is earning its place.** 81% acceptance is high; leave it on. Trying `num_speculative_tokens` 5 or 6 is worth an A/B (*untested*).
3. **`--max-num-seqs 224` is far above the observed peak of 25.** 64 still leaves 2.5x headroom and should reduce the memory held for Mamba blocks (*untested; the saving was not measured*).
4. **`--max-num-batched-tokens` is at its default of 8192.** Prefill peaked at 9.6k tok/s. 16384 may help when many long-context lanes arrive together (*untested*).
5. **`--gpu-memory-utilization` does not size the cache once KV is pinned.** It only sets how much must be free at startup, so keep it low.

## Public tiers
`studio/llm_tiers.py` picks a tier from RAM and VRAM, with exact GGUF files and sampling presets from the Qwen model cards. The crew finds a running server by itself: `STUDIO_LLM_URL`, then vLLM on 8002, llama-server on 8301, Ollama on 11434. `GET /api/llm` shows the pick and the exact command.
