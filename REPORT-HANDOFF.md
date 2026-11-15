# Handoff: finishing the Epistemics sprint report (written 15 Nov 2026 by Fable for Opus 5.5)

Read `MyMemoryVault/FABLE-PLAYBOOK.md` first, then `HANDOFF.md`, `FREEZE.md` and `DEVIATIONS.md` in this folder.

**Deadline: Monday 16 Nov 2026, 17:29 IST. Aim to submit by about noon.** Official Apart template, 4 to 8
pages (8 is a hard cap), required Limitations and Dual-Use appendix. Resubmitting with the exact same title
replaces the PDF. Harsh writes every sentence of the report; you supply figures, tables, numbers and checks.

## State
- Collection is complete. gpt-oss-120b: 320 main, 120 stage two, 80 repeat runs. Llama 3.2 3B, Qwen3.8-27B and
  Nemotron-3-ultra: 160 each.
- All main-condition titles are labelled. 56 titles from the repeat runs (BASE condition) are still unlabelled.
- Blind audit scored: 184 of 200 agree. Relevance marks: 33 of 50 on topic; 15 of 25 real papers on topic.
- Frozen analysis has been run: `results/results.json`. Do NOT change `src/analysis.py` or re-tune anything.
- Workflows in `.github/workflows/` are disabled (private-repo Actions minutes ran out on 14 Nov).

## The numbers (copy from `results/results.json`, never from this note; these are here so you can spot a mistake)
- Primary, gpt-oss-120b, audit notice minus archive notice with ten titles requested: unmatched titles -0.64
  [-1.36, +0.04]; verdict by the frozen rules: inconclusive. Verified papers +0.64 [+0.12, +1.19]. Titles
  given unchanged (9.46).
- Audit-corrected unmatched titles: -1.31 [-1.96, -0.69] (primary arm only, as FREEZE section 12 says).
- Other arms, raw: Llama -0.42, Qwen -0.62, Nemotron -0.20; each inconclusive alone, same direction.
- With permission to list fewer: -0.57 [-1.00, -0.16]. Permission effect itself: -1.80 [-2.54, -1.09].
- Stage two, unmatched withdrawn / real papers withdrawn: neutral 7 of 146 / 4 of 212; audit reminder 104 of
  146 / 67 of 212; real receipts 146 of 146 / 0 of 212. Random deletion would remove about 70 unmatched in the
  audit-reminder branch.

## Still to do, in this order
1. One more labelling pass for the 56 repeat-run titles (`python src/run.py --label`). If some stay
   unlabelled, say so in the report and in DEVIATIONS.md.
2. Add the missing entries to DEVIATIONS.md (facts and times are in the session log
   `session-logs/2026-11-15-epistemics-run-and-tens.md`): the two-Groq-key split of the work; Actions minutes
   running out and collection finishing on the laptop on 14 Nov; the stage-two fix that skips seed-title and
   empty items; any titles left unlabelled.
3. Figure 1: the main contrast for all four models, raw, with the audit-corrected estimate for gpt-oss beside
   it. Intervals shown. Zero line marked.
4. Figure 2: stage two, withdrawals of unmatched titles and of real papers for the three branches, with the
   random-deletion reference.
5. Results table, plus intervals for the stage-two proportions (bootstrap over topics, same seed as the frozen
   analysis; this is a reporting addition, so log it as a deviation).
6. Reference check: every reference Harsh cites is opened and matched to its real record (title, authors,
   year, venue). `REFERENCES-verified.md` has ten already checked. Made-up references can disqualify.
7. README and report both mark pre-existing code (the MSc study's `titles.py`, `lists.py` and verifier logic)
   and name the AI tools used.
8. Harsh writes the prose. You may fix grammar and facts and insert numbers and links. Any sentence you add
   must be flagged to him.
9. Before he submits: the repo must be public only if he says so (grep for secrets first); a push needs his OK.

## How to describe the result honestly
The pre-registered primary is inconclusive. Do not present the audit-corrected estimate as the primary
result; it is the pre-registered correction from section 12 and is reported as such. The stage-two contrast
(a reminder makes the model throw away real papers; real evidence does not) is the clearest finding. The
checker misses some real papers, so "unmatched" is not "fabricated".
