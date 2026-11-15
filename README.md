# Announced audits, actual evidence

Entry for the Apart Research AI x Epistemics Research Sprint, 13 to 15 Nov 2026.

**Question.** When a model is told that its reference list will be checked automatically, does it give fewer
titles that cannot be matched to a real record, beyond what a plain "do not invent titles" instruction and
permission to list fewer already do? And when it is later asked to withdraw titles, does it follow real check
results, or does an audit reminder alone make it throw away real papers too?

DRAFT: Harsh to replace this summary with his own words and the headline numbers once the report is written.

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
| `results/` | `results.json` (frozen analysis), `report_extras.json`, figures, table |
| `tools/` | Runner status, watchdog, audit builder and scorer |
| `fallback/` | The fallback design built before the sprint and not run |

## Run
```
python tests/test_audit.py          # offline checks
python src/analysis.py              # frozen analysis -> results/results.json
python src/report_extras.py         # stage-two intervals, each notice wording -> results/report_extras.json
python src/make_figures.py          # figures and table (needs matplotlib)
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

## AI tools used
- Claude (Anthropic): Claude Fable 5.2 for design discussion; Claude Opus 5.5 for writing and testing the code,
  running the collection, and producing the figures and tables.
- GPT-6-Astra (OpenAI, through the Codex command line) to criticise the design before the freeze.
- Models studied (not tools): gpt-oss-120b and Qwen3.8 27B on Groq, Nemotron 3 Ultra on NVIDIA's hosted API,
  Llama 3.2 3B locally through Ollama.
The plan in `FREEZE.md` and the report are written by Harsh. Harsh did the blind hand audit himself.
