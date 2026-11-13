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
