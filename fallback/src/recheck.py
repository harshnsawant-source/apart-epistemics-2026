"""Second look at sampled titles the study's verifier did not match: search Crossref and OpenAlex.

A hit (similarity >= threshold) means a similar title is indexed elsewhere. No hit means UNRESOLVED,
never "does not exist". Run during the sprint: python src/recheck.py -> data/recheck.json
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_config, norm

UA = {"User-Agent": "citation-recheck/1.0"}


def best(title, candidates):
    """Highest normalised similarity between title and any candidate title."""
    top = {"matched": None, "ratio": 0.0}
    for c in candidates:
        r = SequenceMatcher(None, norm(title), norm(c or "")).ratio()
        if r > top["ratio"]:
            top = {"matched": c, "ratio": round(r, 3)}
    return top


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def crossref(title):
    d = _get("https://api.crossref.org/works?" + urllib.parse.urlencode(
        {"query.bibliographic": title, "rows": 10, "select": "title"}))
    return [t for it in d["message"]["items"] for t in it.get("title", [])]


def openalex(title):
    d = _get("https://api.openalex.org/works?" + urllib.parse.urlencode(
        {"search": title, "per-page": 10, "select": "display_name"}))
    return [w.get("display_name") for w in d["results"]]


SOURCES = {"crossref": crossref, "openalex": openalex}


def classify(per_source, threshold):
    """per_source: {name: {'ratio': float} or {'error': str}}."""
    if any(v.get("ratio", 0) >= threshold for v in per_source.values()):
        return "found_elsewhere"
    if any("error" in v for v in per_source.values()):
        return "lookup_error"          # never treated as unresolved: retry it
    return "unresolved"


def main():
    cfg = load_config()
    items = json.loads((ROOT / "data" / "manifest.json").read_text("utf-8"))["items"]
    out = ROOT / "data" / "recheck.json"
    res = json.loads(out.read_text("utf-8")) if out.exists() else {}
    for it in items:
        if it["auto_label"] != "unmatched" or res.get(it["id"], {}).get("status") in ("found_elsewhere", "unresolved"):
            continue
        per = {}
        for name, fn in SOURCES.items():
            try:
                per[name] = best(it["title"], fn(it["title"]))
            except Exception as e:
                per[name] = {"error": type(e).__name__}
            time.sleep(1.0)
        res[it["id"]] = {"title": it["title"], "sources": per, "status": classify(per, cfg["match_threshold"])}
        out.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    print(Counter(v["status"] for v in res.values()))


if __name__ == "__main__":
    main()
