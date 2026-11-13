"""Health check for the sprint runners. Prints a report; exits 1 if something needs a human (or Claude).

Checks: a runner that should be running is not (restarted automatically with --heal); progress stalled for more
than 90 minutes while work is left; recent failed runs; a runner restarting too fast (a loop).
Run from the repo root after `git pull`. Needs the gh CLI (GH_TOKEN in GitHub Actions).
    python tools/watchdog.py [--heal]
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import design  # noqa: E402
import run  # noqa: E402
from verify import Labeller  # noqa: E402

GH = "gh"
REPO = "harshnsawant-source/apart-epistemics-2026"
STALL_MIN = 90


def sh(args):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def last_commit_age_min(paths):
    out = sh(["git", "log", "-1", "--format=%ct", "--", *paths])
    return (time.time() - int(out)) / 60 if out else None


def main():
    heal = "--heal" in sys.argv
    cfg = design.load_config()
    now = datetime.now(timezone.utc)
    is_open, _ = run.collection_open(cfg, now)
    topics = design.load_json(cfg["topics"])["topics"]
    items = [it for it in design.manifest(cfg, topics) if it["arm"] == "gptoss"]
    have = {r["id"] for r in run.arm_rows("gptoss")}
    gens_left = sum(1 for it in items if it["id"] not in have)
    s2_left = 3 * len(topics) - len(run.stage2_rows("gptoss"))
    lab = Labeller(cfg)
    rows = [r for a in cfg["arms"] for r in run.arm_rows(a)]
    unlabelled = len({t for r in rows for t in r["titles"] if lab.label(t, lookup=False)[0] is None})
    print(f"gpt-oss: {len(have)}/{len(items)} generations, stage two {3 * len(topics) - s2_left}/{3 * len(topics)}; "
          f"unlabelled titles {unlabelled}; collection open {is_open}")

    problems, healed = [], []
    runs = json.loads(sh([GH, "run", "list", "--repo", REPO, "--limit", "40", "--json",
                          "workflowName,status,conclusion,createdAt"]) or "[]")
    needed = []
    if is_open and (gens_left or s2_left > 0):
        needed += ["collect", "collect2"]
    if unlabelled:
        needed.append("label")
    for wf in ("collect", "collect2", "label"):
        mine = [r for r in runs if r["workflowName"] == wf]
        active = [r for r in mine if r["status"] != "completed"]
        recent = [r for r in mine if (now - datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))).total_seconds() < 1200]
        failed = [r for r in mine[:5] if r.get("conclusion") == "failure"]
        if wf in needed and not active:
            if heal:
                sh([GH, "workflow", "run", f"{wf}.yml", "--repo", REPO, "--ref", "master"])
                healed.append(wf)
            else:
                problems.append(f"{wf}: should be running but no run is active or queued")
        if len(recent) > 6:
            problems.append(f"{wf}: {len(recent)} runs started in 20 minutes (restart loop)")
        if len(failed) >= 2:
            problems.append(f"{wf}: {len(failed)} of its last 5 runs failed")

    age = last_commit_age_min(["raw/generations_gptoss.jsonl", "raw/generations_gptoss.s1.jsonl",
                               "raw/generations_gptoss.s2.jsonl", "raw/stage2_gptoss.s1.jsonl", "raw/stage2_gptoss.s2.jsonl"])
    if is_open and (gens_left or s2_left > 0) and age is not None and age > STALL_MIN:
        problems.append(f"gpt-oss: no new data saved for {age:.0f} minutes")
    age_l = last_commit_age_min(["data/recheck_cache.json"])
    if unlabelled and age_l is not None and age_l > STALL_MIN:
        problems.append(f"labelling: no new labels saved for {age_l:.0f} minutes")

    for h in healed:
        print(f"HEALED: {h} was not running; started it again")
    for p in problems:
        print(f"PROBLEM: {p}")
    print("OK" if not problems else "NEEDS ATTENTION")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
