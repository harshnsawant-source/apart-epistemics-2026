# Report outline (15 Nov 2026, Opus 5.5 for Harsh): facts to write from, NOT text to paste

You write every sentence. This file gives, per section, the facts, numbers and files to use. Every number here
was copied from `results/results.json` or `results/report_extras.json` on 15 Nov; check against those files
before it goes in. Anything marked DRAFT is a placeholder for you to rewrite in your own words.

Template (official, from the sprint page): https://docs.google.com/document/d/17b3JWki-ZkaqdmqGI5d0gof-HwlGuWU9Mc1_klNZXKs/copy?usp=sharing
Rules from the page: PDF; at most 8 pages not counting references and appendices; title; abstract of 150 to
250 words; author names and affiliations; required appendix "Limitations and Dual-Use / Ethical
Considerations". Judged 1 to 5 on Impact and Innovation, Execution Quality, Presentation and Clarity.
Deadline Mon 16 Nov 17:29 IST. Resubmitting with the exact same title replaces the PDF.

## Title
Working title in the repo: "Announced audits, actual evidence". Your choice.

## Abstract (150 to 250 words): facts to cover, in this order
1. Question: does telling a model its references will be checked change how many unmatched titles it gives,
   beyond a plain accuracy instruction and permission to list fewer?
2. Design: pre-registered (frozen 13 Nov, before data); 40 topics x 4 conditions x 2 notice wordings on
   gpt-oss-120b (320 requests), plus 3 other models (160 each); every title checked against bibliographic
   records; blind hand audit of 200 titles; then a withdrawal stage with three branches.
3. Primary result: -0.64 unmatched titles per request [-1.36, +0.04]: inconclusive by the frozen rules.
   Verified papers +0.64 [+0.12, +1.19]; titles given unchanged.
4. Same direction in all three other models, none conclusive alone.
5. Clearest finding: an audit reminder made the model withdraw 71% of unmatched titles but also 32% of real
   papers; real check results gave 100% and 0%.
6. One-line takeaway (yours).

## 1. Introduction: facts
- Fabricated references are a known failure; a cheap fix people try is telling the model it will be checked.
- Whether that works, and at what cost to real citations, had not been measured with real verification
  (Ahmed et al. counted DOI-shaped strings only; see Related Work).
- Contributions (your list): the factorial design separating notice, accuracy line and permission; every title
  verified; the withdrawal stage contrasting a reminder with real evidence; pre-registration and audit.

## 2. Related work (all opened and checked: `REFERENCES-verified.md` items 1 to 6, 9)
- Ahmed et al. 2025 (arXiv 2510.08624): closest; evaluation framing changes citation behaviour in GPT-OSS-20B,
  but framing and permission to abstain change together, and DOIs are counted by pattern, not looked up.
- Agrawal et al. 2024 (Findings of EACL): models' own consistency answers flag hallucinated references.
- Zhao et al. 2026 (arXiv 2603.07287): deployment constraints and citation hallucination with Crossref and
  Semantic Scholar checks; an Existing / Unresolved / Fabricated taxonomy close to ours. Their regimes do not
  include an audit announcement.
- Knecht et al. 2026 (arXiv 2605.05835): evaluation awareness has limited effect on behaviour (no citations).
- Mehta 2025 (arXiv 2601.00830): telling models they are watched does not improve hint reporting.
- Goyal 2026 (WASP): verifier-based RL reduces hallucinated references; existence is not relevance.
- Do NOT call this "the Hawthorne effect in LLMs" as a claim.

## 3. Methodology: facts
- Base request: the MSc study's prompt, unchanged (10 titles on a topic, numbered). 40 topics from the MSc study.
- Every condition adds "Accuracy is important; do not invent paper titles."
- Conditions: archival or audit notice x "return 10" or "return fewer if unsure". Two matched 18-word
  wordings per notice (the exact sentences are in `prompts.json`). The database is never named.
- Models: gpt-oss-120b (primary; Groq; reasoning effort low; temperature 0.8; seed per call; up to 2,000
  tokens). Secondary: Qwen3.8 27B (Groq), Nemotron 3 Ultra (NVIDIA API, thinking off), Llama 3.2 3B (local,
  Ollama). Secondary arms used wording 1 only. Qwen and Nemotron were added before their first call
  (deviations 1, 2).
- Scoring: first ten titles; seed titles and repeats dropped. Labels: matched on Semantic Scholar (stored
  lookups), found on Crossref or arXiv, or unmatched (deviations 3, 3b). Similarity threshold 0.90.
- Endpoints: unmatched titles per request (out of 10 slots); guardrail: distinct verified papers per request.
- Statistics: mean within topic, then paired bootstrap over 40 topics, 10,000 resamples, seed 20261115; 95%
  intervals; equivalence margin +/-0.5 with 90% intervals; six outcome rules fixed in FREEZE section 8.
- Audit: 200 gpt-oss titles, 25 per condition x label, blind to condition; correction U(1-p) + Mq per request.
- Stage two: first archival list per topic (40), continued in three branches (neutral, audit reminder, real
  check results); model answers KEEP or WITHDRAW for items 4 to 13; compared with random deletion.
- Collection: 13 Nov 19:47 IST to 14 Nov 23:17 IST, all inside the frozen window; deviations 4 to 8.

## 4. Results: facts (Figure 1, Table 1, Figure 2)
- Figure 1 (`results/fig1_main_contrast.pdf`): the main contrast for all four models, raw, plus the gpt-oss
  audit-corrected estimate.
- Table 1 (`results/table1.md`): cell means, contrasts, verdicts, secondary analyses.
- Primary (gpt-oss): unmatched 3.71 (archival) to 3.08 (audit); change -0.64 [-1.36, +0.04]; inconclusive.
  Verified papers +0.64 [+0.12, +1.19]. Titles given 9.46 in both.
- Audit-corrected (pre-registered, section 12): -1.31 [-1.96, -0.69]. Report it beside the primary, not as it.
- Each wording alone: wording 1 -0.35 [-1.30, +0.55]; wording 2 -0.93 [-1.90, +0.00].
- Other models: Qwen -0.62 [-1.65, +0.33]; Nemotron -0.20 [-0.95, +0.57]; Llama -0.42 [-1.10, +0.23].
  Nemotron gave more titles under the audit notice (+1.07 [+0.25, +2.10]) and more verified papers (+1.27).
- Permission to list fewer, on gpt-oss: cut unmatched by 1.80 [1.09, 2.54], about three times the audit
  notice's point estimate; the audit notice still helped on top of it (-0.57 [-1.00, -0.16]). No interaction
  (+0.06 [-0.62, +0.75]).
- Repeatability: two fresh runs of the unmodified prompt differ by 2.275 unmatched titles on average (40 topics,
  all 80 repeats scored): single requests are noisy, which is why topics are averaged.
- Figure 2 (`results/fig2_stage2.pdf`), stage two, 146 unmatched and 212 verified items across 40 lists:
  neutral 7/146 and 4/212; audit reminder 104/146 (71% [54, 85]) and 67/212 (32% [17, 48]), against 48% of
  each under random deletion; real check results 146/146 and 0/212.
- Stage-two intervals are a reporting addition (deviation 9), not pre-registered.

## 5. Discussion: points to consider (your judgement)
- The notice moves things the right way in every model, but by less than the margin I could detect with 40
  topics; permission to list fewer matters more.
- A reminder alone makes withdrawal indiscriminate-ish (better than random, but loses a third of real papers);
  given evidence, the model follows it exactly. Practical message: give models check results, not threats.
- The receipts branch tests following evidence, not detecting fakes (FREEZE section 10).

## Appendix: Limitations and Dual-Use / Ethical Considerations (required): facts
Limitations (FREEZE section 13 plus what happened):
- One researcher; two notice wordings; 40 topics (small effects undetectable); one primary deployment.
- "Unmatched" is not "fabricated": 8 of 100 audited unmatched titles were real papers the checker missed;
  8 of 100 audited matched titles were not real.
- The audit-corrected estimate rests on small counts (0 of 25 vs 4 of 25 real papers among audited unmatched
  titles, archival vs audit) and its interval ignores the audit's own sampling error.
- Relevance: 33 of 50 audited titles judged on topic; existing is not relevant.
- Low reasoning effort for gpt-oss; thinking off for Nemotron; Groq may update models.
- The "fewer" sentence conflicts with the base request's numbering.
- Stage two's real-results branch uses the same checker whose errors are measured.
- Collection incidents (deviations 4 to 8): lost first run, sources changed, key split, laptop finish.
Dual-use / ethics:
- No human subjects beyond the author's own audit. Only public model APIs and bibliographic APIs, at low
  request rates.
- A finding that reminders make models drop real citations could be misused to suppress legitimate sources;
  the result argues for supplying verification evidence instead.
- Verification services have blind spots (web-only papers), so automated "unmatched" flags should not be shown
  to readers as "fake".

## Must also appear
- Mark pre-existing work (MSc study code and data) and name the AI tools used: see `README.md`.
- Every reference opened and matched to its real record (`REFERENCES-verified.md`).
