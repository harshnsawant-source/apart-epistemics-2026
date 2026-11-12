# Runbook: sprint weekend (Fri 13 to Mon 16 Nov 2026, times IST)

Collection of gpt-oss-120b runs in GitHub Actions every hour (`.github/workflows/collect.yml`), so it keeps
going while you travel on Saturday. Llama runs on the laptop on Friday night.

## Once, before Friday 19:45
1. Allow pushing workflow files:  `! gh auth refresh -h github.com -s workflow`  (opens the browser).
2. Put the Groq key in the repo as a secret, without showing it anywhere. In PowerShell:
   `[Environment]::GetEnvironmentVariable('GROQ_API_KEY','User') | gh secret set GROQ_API_KEY --repo harshnsawant-source/apart-epistemics-2026`
   (or paste it yourself under the repo's Settings > Secrets and variables > Actions).
3. Write `FREEZE.md` (from `FREEZE-outline.md`) and approve the prompts: save `prompts.DRAFT.json` as
   `prompts.json` and set `"prompts": "prompts.json"` in `config.json`.

## Friday after the 19:45 logistics talk
4. (Done 13 Nov, 03:15 IST) FREEZE.md, prompts.json and config.json committed and pushed before kickoff.
   The runner cannot collect before 19:45 IST; the first hourly run after that (20:37 IST) starts by itself.
5. To start sooner, right after the talk:  `gh workflow run collect`
   Check it in the repo's Actions tab: the log should show new generation calls and "labels: N titles still
   unlabelled". If Semantic Scholar blocks GitHub's servers, labels stay unlabelled; the laptop can label on Sunday.
6. On the laptop (Ollama running):  `python src/run.py --arm llama --minutes 240 --no-verify`  (about 1 hour,
   160 calls). Then commit and push `raw/generations_llama.jsonl`. The cloud runner labels those titles too.

## Saturday (travelling)
Nothing. The runner continues every hour, stops for Groq's daily limit and resumes after it resets.
Progress is committed to the repo each hour (see the Actions tab or `git pull`).

## Sunday
7. `git pull`. Check progress: `python src/run.py --arm gptoss --minutes 1 --no-verify` prints N/400 collected.
8. Label anything left on the laptop: `python src/run.py --arm gptoss --minutes 120` (collects nothing once
   done, then labels and runs stage two).
9. Blind audit of 200 labelled titles (tool to be generated from the data, condition hidden).
10. `python src/analysis.py` -> `results/results.json`. Write the report.

## Monday
11. Finish the report, check every reference against REFERENCES-verified.md, submit by about 12:00 IST
    (deadline 17:29 IST). Resubmitting with the exact same title replaces the earlier version.

## If something goes wrong
- Runner keeps failing: the Actions log says why. Collection resumes from the last saved call.
- Groq quota tighter than expected: the run already collects in priority order (FREEZE section 5): both
  notice wordings of the main conditions first, then stage two, then the A/A repeats. So a shortfall drops the
  repeats first, then stage two. Both notice wordings are part of the primary endpoint and are never dropped.
- Disable the hourly runner after collection: repo Actions tab > collect > Disable workflow.
