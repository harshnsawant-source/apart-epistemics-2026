# Deviations from FREEZE.md

Any change after the first study reply is recorded here with the time (IST) and the reason.

## 1. Third model added: Qwen 3.8 27B (Fri 13 Nov 2026, 19:46 IST, before any Qwen data)

What: a third arm, `qwen/qwen3.8-27b` on Groq, run like the Llama replication (four conditions, 40 topics,
notice wording 1, 160 calls; no stage two, no A/A repeats; temperature 0.8, a different seed per call, up to 2,000
output tokens). Collected by the same hourly cloud runner after gpt-oss in each run.

Why: Llama 3.2 3B is small; a second large model from a different family tests whether a gpt-oss result holds
beyond one model family. It runs unattended and has its own Groq quota, so it does not slow the primary arm.
Smoke test on a non-study topic before kickoff: about 270 tokens per call, replies parse cleanly.

What does not change: the primary endpoint, the primary model (gpt-oss-120b) and its call order (checked by
code: adding the arm leaves the gpt-oss and Llama order identical). The Qwen arm is secondary and exploratory,
analysed exactly like the Llama arm (section 9 rules).

## 2. Fourth model added: Nemotron 3 Ultra (Fri 13 Nov 2026, 19:58 IST, before any Nemotron data)

What: a fourth arm, `nvidia/nemotron-3-ultra-550b-a55b` on NVIDIA's hosted API (free developer key, scope "Public
API Endpoints"), run like the Llama and Qwen arms (four conditions, 40 topics, notice wording 1, 160 calls; no stage
two, no A/A repeats; temperature 0.8, a different seed per call, up to 2,000 output tokens). Thinking is switched
OFF (`enable_thinking: false`): with thinking on, 3 of 5 smoke-test calls spent all 2,000 tokens reasoning and
returned no list (raw/smoke_nemotron_thinking_on.jsonl). With thinking off: about 300 tokens per call, 5 of 5 full
lists (raw/smoke_nemotron.jsonl). Both smoke tests used a non-study topic.

Why: with gpt-oss-120b (large), Nemotron 3 Ultra (large, a different developer), Qwen 3.8 27B (medium) and Llama
3.2 3B (small), the secondary arms cover model size and developer. Collected by the hourly cloud runner after
gpt-oss and Qwen; runs only once the NVIDIA_API_KEY repository secret exists.

Differences to state in the report: Nemotron runs with thinking off while gpt-oss runs at low reasoning; NVIDIA's
free-tier limits were not documented when added.

What does not change: the primary endpoint and primary model. Adding the arm leaves the gpt-oss, Llama and Qwen
call orders identical (checked by code; new arms go last in `arm_order`). Secondary and exploratory, analysed
like the other secondary arms (section 9 rules).
