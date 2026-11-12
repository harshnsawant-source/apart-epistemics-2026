---
type: preregistration
created: 2026-11-13
status: frozen
---

# Frozen plan: does announcing a reference check change what a model cites?

Apart Research AI x Epistemics Research Sprint, 13 to 15 Nov 2026. Written and committed on 13 Nov 2026,
before the sprint kickoff and before any study reply was collected. Nothing here changes after the first study
reply; any change goes in `DEVIATIONS.md` with the time and the reason.

## 1. Question and claims

Question: When gpt-oss-120b is told its reference list will be checked, does the number of unmatched titles
change, beyond the effect of a plain accuracy instruction and beyond permission to list fewer than ten?

Primary claim: With ten references requested and the same accuracy instruction in both arms, an audit
announcement changes the number of unmatched titles per request compared with an archival notice, on 40 fixed
topics.

Not claimed: that the model believes it is being watched or knows which titles are invented; that unmatched
titles are fake (an unmatched title is one this pipeline found no record for, see section 7); that the result
holds for other prompts, wordings, models or deployments.

## 2. Previous work

The Ahmed et al. paper (arXiv 2510.08624) used only one model (GPT-OSS-20B). They ran 6 scenarios, each as a
pair of prompts (A/B testing). The content and decoding parameters remained the same between prompts. However,
the prompts were either evaluation or real prompts, and varied in the level of reasoning. One scenario requested
citations. The evaluation prompt requested exactly 3 unique DOIs. The real prompt requested up to 3 DOIs if
certain, otherwise uncertainty. The strictness caused the model to go from avoiding DOIs (0 DOIs) to cautious
responses that fit the structure but were not reliable. The paper counts DOI-like strings with a pattern match
(section 7.2.2); the DOIs were not checked against any database.

Agrawal et al. (Findings of EACL 2024) showed that hallucinated references can partly be detected without
outside resources, by using consistency prompts to question the model about its own references.

This study improves by:
- Separating the audit announcement from the accuracy instruction and from permission to list fewer. (The
  Ahmed et al. prompts change strictness and the number of citations together.)
- Checking every title against bibliographic databases, not just its format.
- Recording the number of verified papers lost. This makes it clear whether less fabrication is happening or
  less citing.

Checked references: `REFERENCES-verified.md`.

## 3. What existed before the sprint

Reused from the MSc study: the title extractor (copied unchanged), the 40 topics with their coverage measure,
and the Semantic Scholar lookup cache (about 7,700 successful lookups merged from the main study and the
extension's gpt-oss and Llama runs; failed lookups removed). The Semantic Scholar checking rule is the same as
the MSc study's (title match at 0.90 or above, failed lookups never cached), reimplemented in this repository.
The cache only holds successful lookups, so titles already seen in the MSc study are scored from stored
records; this applies equally to all conditions.

Written on 12 and 13 Nov 2026, before the sprint kickoff: all code in this repository (conditions and run
order, collection, the Crossref and OpenAlex second look for titles Semantic Scholar misses, stage two, the
analysis, the tests and the hourly runner), this plan, and a smoke test on three NON-study topics used only to
measure token use and check formatting (`raw/smoke_*.jsonl`, not study data). The analysis uses this
repository's own topic-level paired bootstrap; evalnoise is not used. Only the study data is collected during
the sprint.

## 4. Prompts

Prompts are frozen in `prompts.json`. Every experimental condition contains the base request (the MSc prompt,
unchanged) and the accuracy sentence; the A/A repeat runs use the base request only. Experimental conditions
vary the notice (archival or audit) and the quantity line (requested ten, or permission to give fewer). There
are two matched notice wordings of 18 words each; the database is never named.

Token counts: base request 144 tokens; each experimental condition 185 tokens (measured on one non-study test
topic, wording 1).

In the "fewer" condition the permission sentence deliberately conflicts with the base's "through item 13";
following either is data. The control is an archival notice, not an empty prompt, so both arms carry an extra
sentence of the same length about what happens to the list; only whether titles are checked and failures
flagged differs.

## 5. Models

Primary: openai/gpt-oss-120b on Groq at reasoning_effort "low", temperature 0.8, a different seed per call, up
to 2,000 output tokens. At the default setting the design cannot finish under Groq's daily token cap (a test
call used about 1,440 tokens at the default and about 530 at "low"; the design needs about 850,000 and about
350,000 tokens respectively, against a cap of 200,000 per day); the MSc baseline (run at the default) is
therefore context only. Replication: llama3.2:3b Q4_K_M in Ollama on the laptop. Claude Sonnet is not run: it
cannot run unattended while I travel, and it is not needed for the primary result.

If Groq quota runs short: drop the A/A repeat runs first, then stage two. Both notice wordings are part of the
primary endpoint and are never dropped. Llama does not use Groq quota; it stops only if collection time runs
out. The run collects in this order: all main conditions (both wordings), then stage two, then the A/A repeats.

## 6. Collection

Calls: gpt-oss-120b 320 main (40 topics x 4 conditions x 2 wordings), 120 stage two, 80 A/A repeats;
Llama 160 main (wording 1). Order: topic x wording blocks are shuffled, and the four conditions are shuffled
within each block (seed 20261113).

A transport error (timeout, connection failure, 5xx, rate-limit response) is retried up to 3 times with
backoff within the same run. Every attempt, failed or not, is logged with its time and error. A call still
failing after 3 retries is logged as failed and picked up by the next hourly run. The daily quota limit is not
retried: it stops the run until Groq resets the quota. Any other non-transport error (for example an invalid
key or a malformed request) stops the run.

No reply is ever regenerated because of its content. Refusals, short lists and malformed replies are kept as
data.

Window: collection starts after the sprint kickoff (Fri 13 Nov, 19:45 IST) and stops at Sun 15 Nov 2026,
18:00 IST. Any calls not made by then are reported as missing. Labelling and analysis may continue after the
cutoff; new model calls may not.

## 7. Scoring

The first ten titles of each reply are scored; seed titles and repeats are dropped. Each title gets one label:
- Matched: found on Semantic Scholar (title similarity 0.90 or above).
- Found: missed on Semantic Scholar but found on Crossref or OpenAlex at the same threshold.
- Unmatched: cannot be found on any of the three. (In the code: `unresolved`.)
A title whose lookup failed has no label yet and is retried; it is never counted as unmatched.

Unmatched does not mean fabricated. It means there was no match for the title in this pipeline. In the
12 Nov hand check of the MSc extension (96 titles), 8 of the 9 disagreements were real papers the verifier
did not find.

## 8. Margins and outcomes

Margins: guardrail -0.5 verified paper per request; equivalence bounds +/-0.5 unmatched title per request.
Half a title in ten slots is the smallest change I would call meaningful. With 40 topics the detectable
difference is larger than this, so a null result will most likely be inconclusive rather than show
equivalence.

The outcome is decided by the first rule that applies, in this order. "Change" means audit announcement minus
archival notice, with ten titles requested, on gpt-oss-120b.
1. Real but small: the 95% interval for the change in unmatched titles excludes zero, but the 90% interval lies
   entirely within +/-0.5. The direction (decrease or increase) is reported. This is a real effect smaller
   than the smallest change I would call meaningful.
2. Works: the 95% interval for the change in unmatched titles is below zero, and the lower bound of the 95%
   interval for the change in verified papers is above -0.5.
3. Works by citing less: the 95% interval for unmatched titles is below zero, but the lower bound for verified
   papers is at or below -0.5.
4. Increases unmatched titles: the 95% interval for the change in unmatched titles is above zero.
5. No meaningful effect: the 90% interval for the change in unmatched titles lies entirely within +/-0.5.
6. Inconclusive: none of the above.
If fewer than two topics have both cells scored, the result is reported as "not enough data".

## 9. Secondary analyses

All of these analyses are secondary and descriptive: the audit effect under permission to give fewer; the
effect of the permission itself; the audit x permission interaction; each notice wording separately; the
number of titles given; the A/A repeat difference; the Llama replication. A result supports something only if
it points the same way as the primary result with an interval that excludes zero. None can replace the primary
result.

## 10. Stage two: withdrawal

The first archival-notice, ten-title list for each topic (gpt-oss-120b, wording 1) is continued in three
branches; the model answers KEEP or WITHDRAW for items 4 to 13 and gives no new titles.
- Neutral branch: shows how much withdrawal happens when the model is just asked to reconsider.
- Audit-reminder branch: shows whether the announcement adds to that. Neither of these two branches shows the
  model knows which titles are fake.
- Real-results branch: tests whether the model follows evidence it is given, not whether it can detect fakes
  itself.
Each branch is compared with random deletion of the same number of titles.

## 11. Statistics

Outcomes are averaged within each topic first, then compared with a paired bootstrap over the 40 topics:
10,000 resamples, seed 20261115. Effects are reported as absolute differences with 95% percentile intervals;
the equivalence check uses 90% intervals. A topic enters a comparison only if both of its cells were scored,
and the number of topics in each comparison is reported.

## 12. Label audit

About 200 scored titles are checked by hand without knowing the condition, spread across conditions, match
status and topic coverage; 50 of them are also judged on-topic or off-topic. Agreement with the verifier is
reported per label, overall and by condition. The primary result is always reported twice: as measured, and
corrected for the audit's error rates. For each condition, p is the share of audited unmatched titles that
turned out to be real papers, and q is the share of audited matched titles that turned out not to be real.
Each request's unmatched count becomes U x (1 - p) + M x q, where M is its matched-title count, and the same
primary comparison is rerun on the corrected counts. If a condition has fewer than 20 audited titles in a
label, the pooled rate across conditions is used. Any difference between the two results is discussed as a
limitation. The primary endpoint does not change.

## 13. Limitations

- One researcher, no independent replication.
- Two notice wordings.
- 40 topics, so small effects can't be seen.
- Labels come from a search pipeline, not from ground truth.
- A title existing doesn't mean it's relevant or the right citation.
- Low reasoning effort differs from the baseline setting.
- One primary model and deployment.
- Groq may update the deployed model during the weekend.
- The "fewer" sentence conflicts with "through item 13" in the base request.
- Stage two's real-results branch uses the same search pipeline whose labels are being measured.
