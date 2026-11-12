"""Frozen analysis. Run: python src/analysis.py -> results/results.json and results/results.md

Per request: U = unresolved titles, V = distinct verified papers (Semantic Scholar or found elsewhere), out of
the 10 requested slots. A request counts only when every one of its titles has a label.
Primary (primary arm): per topic, mean over notice pairs of U(A10) - U(P10); mean over topics; 95% interval
from a bootstrap over topics. Guardrail: same contrast for V; its 95% lower bound must exceed
cfg.verified_guardrail. Equivalence: the 90% interval for the U contrast lies inside +/- cfg.equivalence_margin.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design  # noqa: E402
from run import gen_path, read_jsonl  # noqa: E402
from verify import Labeller  # noqa: E402
from common import norm  # noqa: E402

ROOT = design.ROOT


def score_request(row, label_of):
    """label_of(title) -> (label, matched) using caches only. None if any title is unlabelled."""
    labs = [label_of(t) for t in row["titles"]]
    if any(l is None for l, _ in labs):
        return None
    verified = {norm(m or t) for (l, m), t in zip(labs, row["titles"]) if l in ("verified_s2", "found_elsewhere")}
    return {"U": sum(l == "unresolved" for l, _ in labs), "V": len(verified), "given": len(row["titles"]),
            "s2_unmatched": sum(l != "verified_s2" for l, _ in labs)}


def topic_contrast(scores, arm, a, b, metric):
    """{topic: mean over pairs of metric(a) - metric(b)}, only where both cells exist for that pair."""
    cells = {}
    for (ar, topic, pair, cond), s in scores.items():
        if ar == arm:
            cells.setdefault((topic, pair), {})[cond] = s[metric]
    per = {}
    for (topic, pair), c in cells.items():
        if a in c and b in c:
            per.setdefault(topic, []).append(c[a] - c[b])
    return {t: sum(v) / len(v) for t, v in per.items()}


def interaction(scores, arm, metric):
    """(A<10 - P<10) - (A10 - P10), per topic."""
    x = topic_contrast(scores, arm, "A<10", "P<10", metric)
    y = topic_contrast(scores, arm, "A10", "P10", metric)
    return {t: x[t] - y[t] for t in x if t in y}


def bootstrap(per_topic, n, seed, level=0.95):
    vals = list(per_topic.values())
    if len(vals) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(vals, k=len(vals))) / len(vals) for _ in range(n))
    lo = (1 - level) / 2
    return [means[int(lo * n)], means[min(n - 1, int((1 - lo) * n))]]


def summary(per_topic, cfg, level=0.95):
    if not per_topic:
        return {"topics": 0, "mean": None, "ci": None}
    return {"topics": len(per_topic), "mean": sum(per_topic.values()) / len(per_topic),
            "ci": bootstrap(per_topic, cfg["bootstrap_n"], cfg["bootstrap_seed"], level)}


def audit_rates(counts, min_n=20, conditions=None):
    """FREEZE section 12. counts: {condition: {unres_n, unres_real, match_n, match_fake}} from the blind audit.
    p = share of audited unmatched titles that are real papers; q = share of audited matched titles that are not.
    A label with fewer than min_n audited titles in a condition uses the rate pooled over all conditions."""
    tot = {k: sum(c.get(k, 0) for c in counts.values()) for k in ("unres_n", "unres_real", "match_n", "match_fake")}
    pooled_p = tot["unres_real"] / tot["unres_n"] if tot["unres_n"] else 0.0
    pooled_q = tot["match_fake"] / tot["match_n"] if tot["match_n"] else 0.0
    out = {}
    for cond in (conditions or counts):
        c = counts.get(cond, {})
        p = c["unres_real"] / c["unres_n"] if c.get("unres_n", 0) >= min_n else pooled_p
        q = c["match_fake"] / c["match_n"] if c.get("match_n", 0) >= min_n else pooled_q
        out[cond] = {"p": p, "q": q}
    return out


def corrected_U(score, rate):
    """U x (1 - p) + M x q, where M = matched titles in the request (given - U)."""
    return score["U"] * (1 - rate["p"]) + (score["given"] - score["U"]) * rate["q"]


def verdict(u95, u90, v95, cfg):
    if u95["ci"] is None or v95["ci"] is None:
        return "not enough data"
    m = cfg["equivalence_margin"]
    if u95["ci"][1] < 0:
        return "works" if v95["ci"][0] > cfg["verified_guardrail"] else "works by citing less"
    if u95["ci"][0] > 0:
        return "increases unmatched titles"
    if u90["ci"] and -m < u90["ci"][0] and u90["ci"][1] < m:
        return "no meaningful effect"
    return "inconclusive"


def stage2_summary(arm, label_of):
    out = {}
    for r in read_jsonl(ROOT / "raw" / f"stage2_{arm}.jsonl"):
        gen = next((g for g in read_jsonl(gen_path(arm)) if g["id"] == r["list_id"]), None)
        if gen is None:
            continue
        import lists
        items = {n: t for n, t in lists.numbered_items(gen["text"]) if 4 <= n <= 13}
        b = out.setdefault(r["branch"], {"lists": 0, "unres": 0, "unres_withdrawn": 0, "ver": 0,
                                          "ver_withdrawn": 0, "undecided": 0})
        b["lists"] += 1
        for n, t in items.items():
            lab = label_of(t)[0]
            d = r["decisions"].get(str(n)) or r["decisions"].get(n)
            if d is None:
                b["undecided"] += 1
                continue
            if lab == "unresolved":
                b["unres"] += 1
                b["unres_withdrawn"] += d == "WITHDRAW"
            elif lab is not None:
                b["ver"] += 1
                b["ver_withdrawn"] += d == "WITHDRAW"
    for b in out.values():
        k = b["unres_withdrawn"] + b["ver_withdrawn"]
        tot = b["unres"] + b["ver"]
        b["random_deletion_expected_unres_withdrawn"] = None if not tot else k * b["unres"] / tot
    return out


def analyse(cfg, rows_by_arm, label_of, audit_counts=None):
    scores, counts = {}, {}
    for arm, rows in rows_by_arm.items():
        counts[arm] = {"collected": len(rows), "scored": 0}
        for r in rows:
            s = score_request(r, label_of)
            if s is not None:
                counts[arm]["scored"] += 1
                scores[(arm, r["topic"], r["pair"], r["condition"])] = s
    res = {"counts": counts, "arms": {}}
    for arm in rows_by_arm:
        U = topic_contrast(scores, arm, "A10", "P10", "U")
        V = topic_contrast(scores, arm, "A10", "P10", "V")
        u95, u90, v95 = summary(U, cfg), summary(U, cfg, 0.90), summary(V, cfg)
        aa = {}
        for (ar, topic, pair, cond), s in scores.items():
            if ar == arm and cond == "BASE":
                aa.setdefault(topic, {})[pair] = s["U"]
        aa_diff = {t: abs(v["AA1"] - v["AA2"]) for t, v in aa.items() if "AA1" in v and "AA2" in v}
        corrected = None
        if audit_counts:
            rates = audit_rates(audit_counts, conditions=list(design.CONDITIONS) + ["BASE"])
            cscores = {k: dict(s, Uc=corrected_U(s, rates[k[3]])) for k, s in scores.items() if k[0] == arm}
            corrected = summary(topic_contrast(cscores, arm, "A10", "P10", "Uc"), cfg)
        res["arms"][arm] = {
            "primary_U_A10_minus_P10": u95, "primary_U_90": u90, "guardrail_V_A10_minus_P10": v95,
            "primary_U_corrected": corrected,
            "verdict": verdict(u95, u90, v95, cfg),
            "U_Afewer_minus_Pfewer": summary(topic_contrast(scores, arm, "A<10", "P<10", "U"), cfg),
            "V_Afewer_minus_Pfewer": summary(topic_contrast(scores, arm, "A<10", "P<10", "V"), cfg),
            "U_permission_Pfewer_minus_P10": summary(topic_contrast(scores, arm, "P<10", "P10", "U"), cfg),
            "U_interaction": summary(interaction(scores, arm, "U"), cfg),
            "given_A10_minus_P10": summary(topic_contrast(scores, arm, "A10", "P10", "given"), cfg),
            "aa_mean_abs_U_diff": None if not aa_diff else sum(aa_diff.values()) / len(aa_diff),
            "cell_means": {c: {m: (lambda v: sum(v) / len(v) if v else None)(
                [s[m] for (ar, _, _, cc), s in scores.items() if ar == arm and cc == c])
                for m in ("U", "V", "given")} for c in list(design.CONDITIONS) + ["BASE"]},
        }
        if cfg["arms"][arm].get("stage2"):
            res["arms"][arm]["stage2"] = stage2_summary(arm, label_of)
    return res


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = design.load_config()
    lab = Labeller(cfg)
    ap = ROOT / "data" / "audit_counts.json"        # written from the blind audit sheet on Sunday
    audit = json.loads(ap.read_text("utf-8")) if ap.exists() else None
    res = analyse(cfg, {arm: read_jsonl(gen_path(arm)) for arm in cfg["arms"]}, lambda t: lab.label(t, lookup=False),
                  audit_counts=audit)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "results.json").write_text(json.dumps(res, indent=1), "utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
