"""Report figures and table (15 Nov 2026). Reads ONLY results/results.json and results/report_extras.json,
so every number shown comes from the frozen analysis or the logged reporting additions.

Run (needs matplotlib; run without -I so the user site-packages are visible):
  python src/make_figures.py -> results/fig1_main_contrast.{png,pdf}, results/fig2_stage2.{png,pdf},
                                results/table1.md, results/table1.csv
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
NAMES = {"gptoss": "gpt-oss-120b", "qwen": "Qwen3.8 27B", "nemotron": "Nemotron 3 Ultra", "llama": "Llama 3.2 3B"}
ORDER = ["gptoss", "qwen", "nemotron", "llama"]
UNRES, VER, GREY = "#D55E00", "#0072B2", "#6b6b6b"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 300})


def fmt(x):
    return f"{x:+.2f}"


def fig1(r, margin):
    rows = []
    for a in ORDER:
        p = r["arms"][a]["primary_U_A10_minus_P10"]
        rows.append((NAMES[a] + (" (primary)" if a == "gptoss" else ""), p["mean"], p["ci"], "measured"))
        if a == "gptoss" and r["arms"][a]["primary_U_corrected"]:
            c = r["arms"][a]["primary_U_corrected"]
            rows.append(("gpt-oss-120b, audit-corrected", c["mean"], c["ci"], "corrected"))
    fig = plt.figure(figsize=(6.5, 3.3))
    ax = fig.add_axes([0.30, 0.33, 0.44, 0.64])
    ax.axvspan(-margin, margin, color="#eeeeee", zorder=0)
    ax.axvline(0, color="black", lw=0.8, zorder=1)
    for i, (name, m, ci, kind) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot(ci, [y, y], color=UNRES if kind == "measured" else GREY, lw=2, zorder=2)
        ax.plot(m, y, "o", ms=6, zorder=3, color=UNRES if kind == "measured" else "white",
                mec=UNRES if kind == "measured" else GREY, mew=1.5)
        ax.text(1.03, y, f"{fmt(m)}  [{fmt(ci[0])}, {fmt(ci[1])}]", va="center", fontsize=8,
                transform=ax.get_yaxis_transform(), clip_on=False)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r_[0] for r_ in reversed(rows)])
    ax.set_xlim(-2.4, 1.4)
    ax.set_xticks([-2, -1, 0, 1])
    ax.set_xlabel("Change in unmatched titles per request\n(audit notice minus archival notice, 10 requested)")
    ax.text(0, -0.5, f"+/-{margin:g} margin", ha="center", va="center", fontsize=6.5, color=GREY,
            bbox=dict(fc="#eeeeee", ec="none", pad=0.5))
    ax.set_ylim(-0.75, len(rows) - 0.4)
    fig.text(0.01, 0.01, "Points: mean over 40 topics. Bars: 95% bootstrap interval over topics.\nFilled: as measured; "
             "open: corrected for the blind audit's error rates (primary arm only).", fontsize=6.5, color=GREY)
    for ext in ("png", "pdf"):
        fig.savefig(RES / f"fig1_main_contrast.{ext}", bbox_inches="tight")
    plt.close(fig)


def fig2(x):
    branches = [("neutral", "Neutral\nreconsider"), ("audit", "Audit\nreminder"), ("receipts", "Real check\nresults")]
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    w = 0.36
    for i, (b, label) in enumerate(branches):
        s = x["stage2"][b]
        for j, (key, n, col, name) in enumerate([("unres", "unres_withdrawn", UNRES, "Unmatched titles"),
                                                 ("ver", "ver_withdrawn", VER, "Verified papers")]):
            share = s[f"share_{key}_withdrawn"] * 100
            lo, hi = (v * 100 for v in s[f"share_{key}_withdrawn_ci"])
            xpos = i + (j - 0.5) * w
            ax.bar(xpos, share, w * 0.95, color=col, label=name if i == 0 else None, zorder=2)
            ax.errorbar(xpos, share, yerr=[[share - lo], [hi - share]], color="black", lw=0.8, capsize=2, zorder=3)
            ax.text(xpos, hi + 2, f"{s[n]}/{s[key]}", ha="center", fontsize=7,
                    bbox=dict(fc="white", ec="none", pad=0.3), zorder=5)
        rd = s["random_deletion_share"] * 100
        ax.plot([i - w, i + w], [rd, rd], color="black", ls="--", lw=1, zorder=4,
                label="Random deletion of the same number" if i == 0 else None)
    ax.set_xticks(range(len(branches)))
    ax.set_xticklabels([b[1] for b in branches])
    ax.set_ylim(0, 112)
    ax.set_ylabel("Share withdrawn (%)")
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.text(0.01, 0.01, "gpt-oss-120b, the first archival-notice list per topic (40 lists), items 4 to 13. "
             "Bars: 95% bootstrap interval over topics.", fontsize=6.5, color=GREY)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(RES / f"fig2_stage2.{ext}", bbox_inches="tight")
    plt.close(fig)


def ci_txt(s):
    return "n/a" if not s or s["mean"] is None else f"{fmt(s['mean'])} [{fmt(s['ci'][0])}, {fmt(s['ci'][1])}]"


def table(r, x):
    head = ["Model", "Unmatched, archival (P10)", "Unmatched, audit (A10)", "Change in unmatched [95% CI]",
            "Change in verified papers [95% CI]", "Titles given P10 / A10", "Frozen verdict"]
    rows = []
    for a in ORDER:
        A = r["arms"][a]
        cm = A["cell_means"]
        rows.append([NAMES[a], f"{cm['P10']['U']:.2f}", f"{cm['A10']['U']:.2f}",
                     ci_txt(A["primary_U_A10_minus_P10"]), ci_txt(A["guardrail_V_A10_minus_P10"]),
                     f"{cm['P10']['given']:.2f} / {cm['A10']['given']:.2f}", A["verdict"]])
    sec = []
    g = r["arms"]["gptoss"]
    sec.append(["gpt-oss-120b: audit-corrected change in unmatched (FREEZE 12)", ci_txt(g["primary_U_corrected"])])
    for pair, v in x["per_wording"]["gptoss"].items():
        sec.append([f"gpt-oss-120b, notice wording {pair} alone: change in unmatched", ci_txt(v["U_A10_minus_P10"])])
    for a in ORDER:
        sec.append([f"{NAMES[a]}: audit effect with permission to list fewer", ci_txt(r["arms"][a]["U_Afewer_minus_Pfewer"])])
    for a in ORDER:
        sec.append([f"{NAMES[a]}: effect of the permission itself (P<10 minus P10)",
                    ci_txt(r["arms"][a]["U_permission_Pfewer_minus_P10"])])
    sec.append(["gpt-oss-120b: mean absolute A/A difference in unmatched titles", f"{g['aa_mean_abs_U_diff']:.3f}"])
    with open(RES / "table1.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)
        w.writerow([])
        w.writerows(sec)
    md = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    md += ["| " + " | ".join(row) + " |" for row in rows]
    md += ["", "| Secondary (per request, 40 topics) | Estimate [95% CI] |", "|---|---|"]
    md += ["| " + " | ".join(row) + " |" for row in sec]
    md += ["", "Units: titles per request out of 10 requested slots, averaged within topic, then over 40 topics. "
           "Intervals: 10,000 bootstrap resamples over topics, seed 20261115."]
    (RES / "table1.md").write_text("\n".join(md) + "\n", "utf-8")


def main():
    r = json.loads((RES / "results.json").read_text("utf-8"))
    x = json.loads((RES / "report_extras.json").read_text("utf-8"))
    cfg = json.loads((ROOT / "config.json").read_text("utf-8"))
    fig1(r, cfg["equivalence_margin"])
    fig2(x)
    table(r, x)
    print("wrote fig1, fig2, table1")


if __name__ == "__main__":
    main()
