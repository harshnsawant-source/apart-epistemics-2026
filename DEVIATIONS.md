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

## 3. Title checking: Crossref and OpenAlex; Semantic Scholar from cache only (Fri 13 Nov 2026, about 21:30 IST)

What: titles are checked on Crossref and OpenAlex (same 0.90 similarity rule, in parallel), the same way in every
condition and arm. Semantic Scholar answers are used only where a lookup is already stored (the MSc cache).
"Unmatched" now means: no match on Crossref or OpenAlex, and no stored Semantic Scholar match. Labels: verified_s2
(stored Semantic Scholar match), found_elsewhere (Crossref or OpenAlex match), unresolved (neither).

Why: on the evening of 13 Nov, Semantic Scholar's public API returned "429 too many requests" to almost every
request without an API key, from GitHub's servers and from the laptop alike (15 lookups took 344 s with 3 failures;
single requests returned 429 immediately). At that rate the ~4,500 titles could not be checked before the Sunday
cutoff, and stage two needs checked titles. Decided by Harsh. Applied before any study title was labelled.

Effect: the rule is identical across conditions, so the A10 minus P10 comparison is unaffected in design. Absolute
"unmatched" rates are not comparable with the MSc study, which checked Semantic Scholar first. The blind hand audit
(section 12) measures the checker's errors under this rule, and the audit-corrected result is reported as planned.

## 4. Incident: the first two cloud runs collected data that was not saved (Fri 13 Nov 2026, 19:47 to 20:40 IST)

What happened: the save step ran `git add raw data results`; the `results` folder did not exist yet, so git added
nothing, and the error was hidden. Run 1 made 320 gpt-oss calls and 103 Qwen calls; run 2 was cancelled at about
20:40 IST once the problem was found. None of those replies were saved, so they are not data and are not analysed.
They used most of the day's gpt-oss quota.

Fix: each model's results are now saved (git add -A) and pushed as soon as it finishes, and again if a run is
cancelled or times out; a failed save is reported. The same calls are collected again with the same seeds and order.
Verified on run 3: gpt-oss 12, Qwen 64 and Nemotron 81 replies saved and pushed.
