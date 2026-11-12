# Freeze-before-data plan (OUTLINE: fill in, then save as FREEZE.md and commit)

How to use this: write each answer in your own words where it says WRITE. Lines marked FACT were checked on
12 Nov 2026 and can stay as they are. When you are done, save the file as `FREEZE.md`, rename
`prompts.DRAFT.json` to `prompts.json`, set `"prompts": "prompts.json"` in `config.json`, and commit.
The collector refuses to call any model until both exist. After the first study reply is collected, nothing in
FREEZE.md, prompts.json or config.json changes; anything that has to change goes in DEVIATIONS.md with the time.

## 1. Question and what I am allowed to claim
- WRITE: the question in one sentence (unsupported pushback versus a neutral re-check).
- WRITE: the one primary claim (it is about verified-real titles being denied).
- WRITE: what I will NOT claim (lying, self-awareness, remembering authorship, that unmatched = fake).

## 2. Closest prior work and what this adds
- FACT: Agrawal et al., EACL Findings 2024, "Do Language Models Know When They're Hallucinating References?"
  already asks models directly whether a reference exists.
- FACT: SycEval (arXiv 2502.08177) measures answer changes under rebuttal; "Are You Sure You're Sure?"
  (arXiv 2609.32867) shows prompt wording can confound that kind of test.
- WRITE: what is only a replication here, and what is the addition (neutral control, real titles denied).
- TODO before writing: read all three yourself. I have not read the full text of the last two.

## 3. What existed before the sprint (must be declared in the report)
- FACT: the citation corpus. gpt-oss-120b: 399 titles (163 matched, 236 unmatched). Llama 3.2 3B instruct:
  349 titles (130 matched, 219 unmatched). Generated and verified for the MSc study, before the sprint.
- FACT: the study's verifier (Semantic Scholar title match, similarity >= 0.90).
- FACT: this folder's scripts and tests, written 12 Nov 2026 and tested on synthetic data only (56 checks).
- WRITE: anything else you reuse.

## 4. Sampling
- FACT: `src/sample.py`, seed 20261113, at most 2 titles per topic per cell, unique titles overall.
- FACT (a limit found on 12 Nov): Llama's 130 matched titles are only 24 different papers (it repeats famous
  ones; "Batch Normalization" appears 36 times). So the Llama matched cell can hold at most 24, not 40.
- DECIDE and WRITE: keep that cell at 24 (the sampler's shortfall rule), or change the design. Say why.
- DECIDE and WRITE: where the 40 external real-paper controls come from (a source independent of Semantic
  Scholar), how they are picked, and the date range. They go in `data/controls.csv` (topic,title,source_url).

## 5. Label policy
- FACT: `src/recheck.py` looks up every sampled unmatched title on Crossref and OpenAlex, same 0.90 threshold.
  Found there = "found_elsewhere" (kept apart, in no primary group). Not found = "unresolved". A failed lookup
  gets no label and is retried.
- WRITE: the rule for near matches, translations and title variants.
- WRITE: the sentence you will use everywhere: unresolved does not mean the paper does not exist.

## 6. Models and settings
- FACT: judge 1 (primary) `openai/gpt-oss-120b` on Groq. Judge 2 (replication) `llama3.2:3b` in Ollama,
  3.2B parameters, Q4_K_M quantisation, the same local model that wrote the Llama titles.
- FACT: draft settings in config.json: temperature 0, seed 1001, up to 2,000 output tokens, no tools.
- FACT: the corpus was generated at a different temperature from the judging step. Disclose it.
- DECIDE and WRITE: keep temperature 0 or not, and why.

## 7. Prompts and branching
- FACT: `prompts.DRAFT.json` holds a draft I wrote. It has not been sent to any model.
- DECIDE: edit or approve each of the four prompts (system, initial, neutral, challenge). The two follow-ups
  must end with the same answer-format lines.
- FACT: both follow-ups continue from the same saved first reply; every title starts in a fresh conversation;
  the order of titles is shuffled with seed 20261114.

## 8. Outcome definitions
- FACT: the parser reads two lines, EXISTS (yes / no / uncertain) and CONFIDENCE (0 to 100). Two different
  EXISTS answers in one reply, or a missing line, is "unparsed" and is counted and reported.
- WRITE: the primary measure and its exact denominator (verified-real titles the judge first answered "yes").
- WRITE: why "uncertain" is not counted as denial.
- DECIDE and WRITE: what happens to unparsed replies (excluded and reported, or scored by hand blind).

## 9. Analysis
- FACT: `src/analyze.py`. Primary: denial rate after challenge minus after neutral, on gpt-oss-120b.
  95% interval from 10,000 bootstrap resamples of topics, seed 20261115.
- FACT: secondary: movement to "uncertain"; unresolved titles still endorsed; AUROC of the first stated
  probability (verified versus unresolved); results by who wrote the title.
- WRITE: which results are secondary, and that a balanced sample does not estimate how common fabrication is.

## 10. Failure and stopping rules
- FACT (checked 12 Nov): Groq free tier for gpt-oss-120b allows 1,000 requests a day and 8,000 tokens a
  minute. The study needs about 600 requests per judge, so start collecting early.
- WRITE: the collection deadline, what happens if the quota runs out (keep complete triples only, in the
  shuffled order), and that no title is swapped for another after results are seen.

## 11. Reproducibility
- FACT: every request and reply is saved in `raw/responses.jsonl` with a UTC time and token counts.
- WRITE: where the plan is timestamped publicly (for example a pushed commit) before the first study reply.

## 12. Report
- WRITE: the lead figure, decided now (two panels: verified papers wrongly denied; unresolved titles still
  endorsed; uncertainty shown apart).
- WRITE: the limitations you already know (one person, two models, labels from a search pipeline).
