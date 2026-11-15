"""Reporting additions (written 15 Nov 2026, after the frozen analysis ran; logged in DEVIATIONS.md).

Does NOT change or replace src/analysis.py. It imports the frozen functions and adds:
  1. 95% intervals for the stage-two withdrawal shares (bootstrap over topics, same seed and resample count).
  2. The primary contrast for each notice wording separately (FREEZE section 9 lists it; the frozen script
     does not compute it).
It also re-derives the stage-two totals and the primary contrast and stops if they differ from
results/results.json, so a figure can never disagree with the frozen numbers.

Run: python src/report_extras.py -> results/report_extras.json
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design  # noqa: E402
import lists  # noqa: E402
from analysis import score_request, summary, topic_contrast  # noqa: E402
from run import arm_rows, stage2_rows  # noqa: E402
from verify import Labeller  # noqa: E402

ROOT = design.ROOT


def stage2_by_topic(arm, label_of):
    """{branch: {topic: counts}} with exactly the counting rules of analysis.stage2_summary."""
    gens = {g["id"]: g for g in arm_rows(arm)}
    out = {}
    for r in stage2_rows(arm):
        gen = gens.get(r["list_id"])
        if gen is None:
            continue
        items = {n: t for n, t in lists.numbered_items(gen["text"]) if 4 <= n <= 13}
        c = out.setdefault(r["branch"], {}).setdefault(
            r["topic"], {"unres": 0, "unres_withdrawn": 0, "ver": 0, "ver_withdrawn": 0})
        for n, t in items.items():
            lab = label_of(t)[0]
            d = r["decisions"].get(str(n)) or r["decisions"].get(n)
            if d is None:
                continue
            if lab == "unresolved":
                c["unres"] += 1
                c["unres_withdrawn"] += d == "WITHDRAW"
            elif lab is not None:
                c["ver"] += 1
                c["ver_withdrawn"] += d == "WITHDRAW"
    return out


def ratio_ci(per_topic, num, den, n, seed, level=0.95):
    """Share sum(num)/sum(den); percentile interval from resampling topics with replacement."""
    vals = list(per_topic.values())
    rng = random.Random(seed)
    stats = []
    for _ in range(n):
        s = rng.choices(vals, k=len(vals))
        d = sum(v[den] for v in s)
        stats.append(sum(v[num] for v in s) / d if d else 0.0)
    stats.sort()
    lo = (1 - level) / 2
    return [stats[int(lo * n)], stats[min(n - 1, int((1 - lo) * n))]]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = design.load_config()
    lab = Labeller(cfg)
    label_of = lambda t: lab.label(t, lookup=False)  # noqa: E731
    frozen = json.loads((ROOT / "results" / "results.json").read_text("utf-8"))
    arm = cfg["primary_arm"]
    n, seed = cfg["bootstrap_n"], cfg["bootstrap_seed"]
    out = {"_note": "Reporting additions; see DEVIATIONS.md. Intervals: bootstrap over topics, "
                    f"{n} resamples, seed {seed}.", "stage2": {}, "per_wording": {}}

    # 1. Stage two withdrawal shares with intervals.
    by = stage2_by_topic(arm, label_of)
    for branch, per in by.items():
        tot = {k: sum(v[k] for v in per.values()) for k in ("unres", "unres_withdrawn", "ver", "ver_withdrawn")}
        f = frozen["arms"][arm]["stage2"][branch]
        for k in tot:
            if tot[k] != f[k]:
                raise SystemExit(f"stage two {branch} {k}: {tot[k]} here, {f[k]} in results.json")
        k_all = tot["unres_withdrawn"] + tot["ver_withdrawn"]
        out["stage2"][branch] = {
            "topics": len(per),
            "unres": tot["unres"], "unres_withdrawn": tot["unres_withdrawn"],
            "share_unres_withdrawn": tot["unres_withdrawn"] / tot["unres"],
            "share_unres_withdrawn_ci": ratio_ci(per, "unres_withdrawn", "unres", n, seed),
            "ver": tot["ver"], "ver_withdrawn": tot["ver_withdrawn"],
            "share_ver_withdrawn": tot["ver_withdrawn"] / tot["ver"],
            "share_ver_withdrawn_ci": ratio_ci(per, "ver_withdrawn", "ver", n, seed),
            "random_deletion_share": k_all / (tot["unres"] + tot["ver"]),
            "random_deletion_expected_unres_withdrawn": k_all * tot["unres"] / (tot["unres"] + tot["ver"]),
            "random_deletion_expected_ver_withdrawn": k_all * tot["ver"] / (tot["unres"] + tot["ver"]),
        }

    # 2. Each notice wording separately (all arms that ran it).
    for a in cfg["arms"]:
        scores = {}
        for r in arm_rows(a):
            s = score_request(r, label_of)
            if s is not None:
                scores[(a, r["topic"], r["pair"], r["condition"])] = s
        both = summary(topic_contrast(scores, a, "A10", "P10", "U"), cfg)
        fz = frozen["arms"][a]["primary_U_A10_minus_P10"]
        if abs(both["mean"] - fz["mean"]) > 1e-9 or both["ci"] != fz["ci"]:
            raise SystemExit(f"{a}: primary contrast differs from results.json")
        for pair in cfg["arms"][a]["pairs"]:
            sub = {k: v for k, v in scores.items() if k[2] == pair}
            out["per_wording"].setdefault(a, {})[pair] = {
                "U_A10_minus_P10": summary(topic_contrast(sub, a, "A10", "P10", "U"), cfg),
                "V_A10_minus_P10": summary(topic_contrast(sub, a, "A10", "P10", "V"), cfg),
            }

    (ROOT / "results" / "report_extras.json").write_text(json.dumps(out, indent=1), "utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
