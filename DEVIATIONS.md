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

## 3b. Second-look sources changed to Crossref and arXiv (Sat 14 Nov 2026, about 00:20 IST)

What: titles are checked on Crossref and arXiv (arXiv's own search API, at most one request every 3.1 s, as arXiv
asks). OpenAlex is dropped. The 41 titles labelled earlier with Crossref and OpenAlex were cleared and are checked
again with the new sources, so every title is labelled the same way.

Why: OpenAlex now prices each search (its response headers show 1,000 credits per day without a paid key and 10
credits per search, so about 100 searches a day); from about 23:00 IST it returned "429 too many requests", so no
title could be labelled. DBLP was tested next, but its API sits behind a bot check and cannot be used by a script.
arXiv was tested on 8 titles: it found real arXiv papers that Crossref misses (for example Grokking and Toy Models
of Superposition) and did not match an invented title. Decided by Claude under Harsh's standing instruction to take
the best option when he is away, and reported to him.

Effect: same as deviation 3. Known blind spot: papers published only on the web (for example Anthropic's
Transformer Circuits posts) are found by none of the sources; the hand audit measures this.

## 5. gpt-oss calls split between two runners and two Groq keys (Fri 13 Nov 2026, 22:22 IST, during collection)

What: from 22:22 IST the remaining gpt-oss calls were divided between two cloud runners, each with its own Groq
API key (the second key created by Harsh). Runner k took every second item of the frozen call order (items k-1,
k-1+2, ...), so the two halves never overlap, and each wrote to its own file (`raw/generations_gptoss.s1.jsonl`,
`raw/generations_gptoss.s2.jsonl`; stage two the same way). Until the second key existed, runner 1 made all
gpt-oss calls (from 22:32 IST). Llama, Qwen, Nemotron and title checking moved to a third runner. If two runners
ever saved the same call, only the earlier reply is kept: 3 duplicate main-condition replies were dropped this
way (323 saved, 320 kept).

Why: after the lost run (deviation 4) used most of the first day's gpt-oss quota, one key could not finish the
520 gpt-oss calls before the Sunday cutoff.

Effect: same model, settings, prompts and per-call seeds; each runner follows the frozen order on its half, so
the four conditions stay interleaved in both. Calls ran as two parallel streams instead of one sequence, so the
clock time of each call differs from a single-runner schedule. No reply was regenerated or replaced.

## 6. Collection finished on the laptop after GitHub Actions minutes ran out (Sat 14 Nov 2026, from about 09:15 IST)

What: the private repository's free GitHub Actions minutes ran out on the morning of 14 Nov; the last cloud run
saved at 09:14 IST. The workflows were disabled and the remaining gpt-oss calls (the last stage-two calls, then
all 80 A/A repeat runs) were made from the laptop with the same script, settings and keys. The A/A repeats ran
from 11:19 to 23:17 IST on 14 Nov.

Why: no cloud minutes were left, and the laptop was available.

Effect: none on the design. Same code, and the frozen order of phases was kept (main conditions, then stage two,
then the A/A repeats; FREEZE section 5). Every call was made inside the collection window, which closed on
Sun 15 Nov 2026 at 18:00 IST.

## 7. Stage-two receipts: items that are never scored get no receipt line (Sat 14 Nov 2026, 11:18 IST)

What: the real-results branch waits until every item 4 to 13 of a list has a label. Two lists contained an item
that is never scored (section 7 drops empty items and repeated seed titles), so their receipts could never be
built and stage two stopped at 118 of 120 calls. From 11:18 IST such an item gets no receipt line; the model is
still asked KEEP or WITHDRAW for items 4 to 13. Lists affected: "activation steering" (item 10) and "hypernetworks
for weight generation" (item 4). The fix has an offline test (`tests/test_audit.py`).

Effect: in those two lists the model saw 9 receipt lines instead of 10. Items that are never scored were never
counted in any stage-two total, before or after the fix, so the counting rule is unchanged.

## 8. Two changes to `src/analysis.py` after the first reply (Fri 13 Nov 22:22 IST and Sun 15 Nov 01:07 IST)

What, first: the analysis reads every runner's file (`arm_rows`, `stage2_rows`, one reply per call) instead of
the single file it read before the two-runner split (deviation 5). Made at 22:22 IST on 13 Nov, before any
analysis was run.

What, second: the audit correction (FREEZE section 12) is applied to the primary arm only. The script had applied
it to every arm, but the blind audit sampled gpt-oss titles only, so its error rates say nothing about the other
models; section 12 describes the correction for the primary result. Fixed on 15 Nov at 01:07 IST, when the audit was
scored. Corrected estimates for the other three arms had appeared in a working table before the fix; they are
not reported.

Effect: neither change alters the endpoints, contrasts, intervals or decision rules. The first only changes where
the replies are read from. The second removes corrected estimates for Llama, Qwen and Nemotron that section 12
never planned. No other line of the analysis was changed.

## 9. Reporting additions after the frozen analysis (Sun 15 Nov 2026, from 16:15 IST)

What: `src/report_extras.py` and `src/make_figures.py`, written after the frozen analysis had run. They do not
change `src/analysis.py`; they import its functions and stop with an error if their totals or the primary
contrast differ from `results/results.json`. They add: (a) 95% intervals for the stage-two withdrawal shares
(bootstrap over topics, same seed and resample count as the frozen analysis); (b) the primary contrast for each
notice wording separately, which section 9 lists but the frozen script does not compute; (c) the two figures
and the results table.

Effect: no frozen number changes. The stage-two intervals are not pre-registered and are reported as a
descriptive addition.

## 10. Final labelling pass and one rerun of the frozen analysis (Sun 15 Nov 2026, 16:10 to about 16:45 IST)

What: 56 titles from the A/A repeat runs had no label when the frozen analysis first ran (15 Nov, 01:07 IST),
because lookups had failed. Three more labelling passes (`python src/run.py --label`, same sources and rules)
labelled all of them; no title is left unlabelled. The frozen `src/analysis.py` was then run again, unchanged.

Effect: only the A/A repeat numbers changed (the main conditions and stage two were already fully labelled):
gpt-oss requests scored 384 to 400; mean absolute A/A difference in unmatched titles 2.70 (27 topics) to 2.275
(40 topics); A/A cell means updated. The primary result, the corrected result, every secondary contrast and
stage two are identical to the first run.
