# Announced audits, actual evidence

Entry for the Apart Research AI x Epistemics Research Sprint, 13 to 15 Nov 2026.

**Question.** When a model is told that its reference list will be checked automatically, does it give fewer
titles that cannot be matched to a real record, beyond what a plain "do not invent titles" instruction and
permission to list fewer already do? And when it is later asked to withdraw titles, does it follow real check
results, or does an audit reminder alone make it throw away real papers too?

**Report:** [`report/announced-audits-report.pdf`](report/announced-audits-report.pdf)

**Results.** On gpt-oss-120b (40 topics, 320 requests), the audit notice changed unmatched titles per request by
-0.64 (95% CI -1.36 to +0.04), inconclusive under the frozen rules, while verified papers rose by 0.64 (0.12 to
1.19). Qwen3.8 27B, Nemotron 3 Ultra and Llama 3.2 3B moved in the same direction, none conclusively. Permission to
give fewer titles had a larger effect (-1.80). In stage two, an audit reminder made gpt-oss-120b withdraw 71% of
its unmatched titles but also 32% of its real papers; given the real check results, it withdrew all unmatched
titles and no real ones. In an exploratory run after the cutoff (`DEVIATIONS.md` item 11), the other three
models given the real check results withdrew 95% to 99% of their unmatched titles and 0% to 9% of their real
papers. Telling a model it will be checked has a small effect; showing it the evidence of the check works.

## Where things are
| Path | What |
|---|---|
| `FREEZE.md` | The plan, frozen on 13 Nov 2026 (03:11 IST) before the first study reply |
| `DEVIATIONS.md` | Every change after the freeze, with time, reason and effect |
| `prompts.json`, `config.json` | Frozen prompts and settings (models, seeds, margins, collection window) |
| `src/` | Collection, title extraction, labelling, stage two, analysis |
| `tests/test_audit.py` | Offline checks on synthetic data (no model, no network) |
| `raw/` | Every model reply and every call attempt (`*_attempts.jsonl`), one file per runner |
| `audit/` | The blind hand audit: sheet, filled answers, key, scored result |
| `results/` | `results.json` (frozen analysis), `report_extras.json`, `stage2_addendum.json`, figures, table |
| `report/` | The submitted report (PDF and docx) and its plain-text source |
| `tools/` | Runner status, watchdog, audit builder and scorer, stage-two addendum, report builder |
| `fallback/` | The fallback design built before the sprint and not run |

## Run
```
python tests/test_audit.py          # offline checks
python src/analysis.py              # frozen analysis -> results/results.json
python src/report_extras.py         # stage-two intervals, each notice wording -> results/report_extras.json
python src/make_figures.py          # figures and table (needs matplotlib)
python tools/stage2_addendum.py summary   # exploratory stage two on the other models -> results/stage2_addendum.json
```
Collection (`python src/run.py ...`) needs API keys in environment variables and only runs inside the frozen
collection window. Keys are never stored in this repository.

## Pre-existing work (made before the sprint started on Fri 13 Nov 2026, 19:45 IST)
From Harsh's MSc study on fabricated citations (before 13 Nov 2026):
- `src/titles.py`: the title extractor, copied unchanged.
- The rule for reading a numbered list in `src/lists.py` (reimplemented, same rule).
- The Semantic Scholar checking rule in `src/verify.py` (title similarity 0.90 or above, failed lookups never
  cached; reimplemented).
- `data/preexisting/`: the 40 topics with their coverage measure, and the Semantic Scholar lookup cache.
- The base request text in `prompts.json` (the MSc prompt, unchanged).

Written on 12 and 13 Nov 2026, before the kickoff: everything in `src/` except the two reporting scripts named
below, and `tests/`, `fallback/`,
`tools/start_tonight.py`, the first version of `.github/workflows/collect.yml`, `FREEZE.md`, `prompts.json`,
`config.json`, and the smoke tests on three non-study topics (`raw/smoke_*.jsonl`).

Made during the sprint: all study data in `raw/`, `audit/` and `results/`; the changes listed in
`DEVIATIONS.md`; the second and third runner workflows and the watchdog; `tools/make_audit.py`,
`tools/score_audit.py`, `tools/status.py` changes; `src/report_extras.py` and `src/make_figures.py`.
Made after the collection cutoff (15 Nov 2026): `tools/stage2_addendum.py`, its replies in
`raw/stage2addendum_*.jsonl`, `tools/build_report.py`, and the report in `report/`.

## AI tools used
- Claude (Anthropic): Claude Fable 5.2 for design discussion; Claude Opus 5.5 for writing and testing the code,
  running the collection, producing the figures and tables, and writing a first draft of the report.
- GPT-6-Astra (OpenAI, through the Codex command line) to criticise the design before the freeze.
- Models studied (not tools): gpt-oss-120b and Qwen3.8 27B on Groq, Nemotron 3 Ultra on NVIDIA's hosted API,
  Llama 3.2 3B locally through Ollama.
The plan in `FREEZE.md` is written by Harsh, and he rewrote the report from Claude's draft. Harsh did the blind
hand audit himself.
