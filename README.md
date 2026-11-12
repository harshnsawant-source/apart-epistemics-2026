# Cited, then disowned? (working title)

Entry for the Apart Research AI x Epistemics Research Sprint, 13 to 15 Nov 2026.

**Question.** When a user says "I could not find this paper", do models withdraw only the titles that cannot be
verified, or do they also deny papers that exist? Each title gets a first judgement, then a neutral re-check and
a pushback that both continue from the same first reply.

## Status
Scaffold only. No study response has been collected. Nothing here is a result.

## What existed before the sprint
- The citation corpus and its verifier, from an MSc study (generated and verified before 13 Nov 2026).
- Everything in this folder as of the first commit: scripts, tests and the outline, written on 12 Nov 2026 and
  run on synthetic data only.

## Layout
| Path | What |
|---|---|
| `FREEZE-outline.md` | The plan to fill in and commit as `FREEZE.md` before any data. |
| `config.json`, `prompts.DRAFT.json` | Draft settings and draft prompts. |
| `src/sample.py` | Seeded sample of titles: matched and unmatched per generator, plus external real controls. |
| `src/recheck.py` | Second lookup (Crossref, OpenAlex) for unmatched titles. No hit means unresolved, not fake. |
| `src/collect.py` | Resumable collection. Refuses to run until the plan and prompts are frozen. |
| `src/parse.py` | Reads EXISTS and CONFIDENCE from a reply; flags anything unclear. |
| `src/analyze.py` | Paired contrasts with a topic-level bootstrap, and AUROC. |
| `tests/test_all.py` | 56 offline checks on synthetic data. |

## Run
```
python tests/test_all.py     # offline checks
python src/sample.py         # data/manifest.json
python src/recheck.py        # data/recheck.json
python src/collect.py        # raw/responses.jsonl (needs FREEZE.md and frozen prompts)
python src/analyze.py        # results/
```
Standard library only. The Groq key is read from the `GROQ_API_KEY` environment variable and is never stored.
