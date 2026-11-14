"""Score the blind audit (FREEZE section 12). Reads audit/audit_filled.csv and audit/audit_key.json and writes
data/audit_counts.json (used by the analysis for the audit-corrected result) and audit/audit_result.json.
    python tools/score_audit.py
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def counts(rows, key):
    """{condition: {unres_n, unres_real, match_n, match_fake}} plus agreement summaries."""
    out, agree, n = {}, 0, 0
    rel = {"on": 0, "off": 0}
    for r in rows:
        k = key[str(r["id"])]
        v = (r.get("verdict") or "").strip()
        if v not in ("real", "fabricated"):
            continue
        c = out.setdefault(k["condition"], {"unres_n": 0, "unres_real": 0, "match_n": 0, "match_fake": 0})
        n += 1
        if k["group"] == "unmatched":
            c["unres_n"] += 1
            c["unres_real"] += v == "real"
            agree += v == "fabricated"
        else:
            c["match_n"] += 1
            c["match_fake"] += v == "fabricated"
            agree += v == "real"
        if (r.get("relevance") or "") in rel:
            rel[r["relevance"]] += 1
    return out, {"audited": n, "agree": agree, "agreement": None if not n else agree / n, "relevance": rel}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    key = json.loads((ROOT / "audit" / "audit_key.json").read_text("utf-8"))
    rows = list(csv.DictReader((ROOT / "audit" / "audit_filled.csv").open(encoding="utf-8-sig")))
    c, summary = counts(rows, key)
    (ROOT / "data" / "audit_counts.json").write_text(json.dumps(c, indent=1), "utf-8")
    (ROOT / "audit" / "audit_result.json").write_text(json.dumps({"per_condition": c, **summary}, indent=1), "utf-8")
    print(json.dumps({"per_condition": c, **summary}, indent=1))


if __name__ == "__main__":
    main()
