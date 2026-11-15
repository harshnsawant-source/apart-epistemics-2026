"""Stage-two addendum for the secondary models (DEVIATIONS.md item 11; added 15 Nov 2026, after the cutoff).

NOT pre-registered. Runs the frozen stage-two procedure, unchanged, on Qwen, Nemotron and Llama: same lists
(pair-1 P10, one per topic), same three branches, same prompts, same receipts built from the same cached labels,
same seed scheme, same settings per model. Only difference: it runs after the frozen collection cutoff, so it
does not go through run.py's collection window. Frozen code, config and results are not touched.

Output: raw/stage2addendum_<arm>.jsonl (separate from the pre-registered raw/stage2_gptoss*.jsonl files).

    python tools/stage2_addendum.py run --arm qwen --minutes 60
    python tools/stage2_addendum.py summary        # -> results/stage2_addendum.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import design  # noqa: E402
import report_extras  # noqa: E402
import run  # noqa: E402
from llm import DailyLimit  # noqa: E402
from verify import Labeller  # noqa: E402

ARMS = ("qwen", "nemotron", "llama")


def out_path(arm):
    return ROOT / "raw" / f"stage2addendum_{arm}.jsonl"


def rows(arm):
    p = out_path(arm)
    return run._first_per_id(run.read_jsonl(p)) if p.exists() else []


def do_run(cfg, prompts, arm, minutes):
    spec = cfg["arms"][arm]
    lab = Labeller(cfg)
    call = run.make_call(spec)
    out = out_path(arm)
    done = {r["id"] for r in rows(arm)}
    lists_ = sorted((r for r in run.arm_rows(arm) if r["pair"] == "1" and r["condition"] == "P10"),
                    key=lambda r: r["id"])
    deadline = time.time() + minutes * 60
    made = skipped = 0
    for r in lists_:
        for b in run.BRANCHES:
            sid = f"{r['id']}|{b}"
            if sid in done:
                continue
            if time.time() > deadline:
                return made, skipped, "time"
            msgs = run.stage2_messages(prompts, r, b, lab)
            if msgs is None:
                skipped += 1
                continue
            try:
                res = run.attempt(call, (spec["backend"], spec["model"], msgs, cfg["temperature"],
                                         design.call_seed(cfg["base_seed"], sid), cfg["max_completion_tokens"]),
                                  sid, out.with_name(out.stem + "_attempts.jsonl"))
            except DailyLimit as e:
                return made, skipped, f"daily limit: {e}"
            if res is None:
                continue
            run.append_jsonl(out, {"id": sid, "list_id": r["id"], "topic": r["topic"], "branch": b,
                                   "messages": msgs, "text": res["text"],
                                   "decisions": run.parse_decisions(res["text"]),
                                   "usage": res.get("usage"), "utc": run.now()})
            made += 1
    return made, skipped, "done"


def do_summary(cfg):
    lab = Labeller(cfg)
    label_of = lambda t: lab.label(t, lookup=False)  # noqa: E731
    n, seed = cfg["bootstrap_n"], cfg["bootstrap_seed"]
    out = {"_note": "NOT pre-registered; collected after the frozen cutoff (DEVIATIONS.md item 11). "
                    "Counting rules identical to the frozen stage-two summary. Intervals: bootstrap over topics, "
                    f"{n} resamples, seed {seed}.", "arms": {}}
    for arm in ARMS:
        rs = rows(arm)
        if not rs:
            continue
        report_extras.stage2_rows = lambda a, _rs=rs: _rs     # count this addendum's replies
        by = report_extras.stage2_by_topic(arm, label_of)
        parsed = sum(1 for r in rs if r["decisions"])
        res = {"replies": len(rs), "replies_with_decisions": parsed, "branches": {}}
        for branch, per in by.items():
            tot = {k: sum(v[k] for v in per.values()) for k in ("unres", "unres_withdrawn", "ver", "ver_withdrawn")}
            k_all = tot["unres_withdrawn"] + tot["ver_withdrawn"]
            res["branches"][branch] = {
                "topics": len(per), **tot,
                "share_unres_withdrawn": tot["unres_withdrawn"] / tot["unres"] if tot["unres"] else None,
                "share_unres_withdrawn_ci": report_extras.ratio_ci(per, "unres_withdrawn", "unres", n, seed),
                "share_ver_withdrawn": tot["ver_withdrawn"] / tot["ver"] if tot["ver"] else None,
                "share_ver_withdrawn_ci": report_extras.ratio_ci(per, "ver_withdrawn", "ver", n, seed),
                "random_deletion_share": k_all / (tot["unres"] + tot["ver"]) if tot["unres"] + tot["ver"] else None,
            }
        out["arms"][arm] = res
    (ROOT / "results" / "stage2_addendum.json").write_text(json.dumps(out, indent=1), "utf-8")
    print(json.dumps(out, indent=1))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run", "summary", "check"))
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--minutes", type=float, default=60)
    a = ap.parse_args()
    cfg = design.load_config()
    design.guard(cfg)
    prompts = design.load_json(cfg["prompts"])
    if a.cmd == "check":
        lab = Labeller(cfg)
        for arm in ARMS:
            ls = [r for r in run.arm_rows(arm) if r["pair"] == "1" and r["condition"] == "P10"]
            ready = sum(1 for r in ls if run.stage2_messages(prompts, r, "receipts", lab) is not None)
            print(f"{arm}: {len(ls)} lists, {ready} fully labelled, {len(rows(arm))} addendum replies saved")
    elif a.cmd == "run":
        made, skipped, why = do_run(cfg, prompts, a.arm, a.minutes)
        print(f"{a.arm}: {made} new calls ({why}); {skipped} skipped (unlabelled); {len(rows(a.arm))} saved")
    else:
        do_summary(cfg)


if __name__ == "__main__":
    main()
