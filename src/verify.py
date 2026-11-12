"""Label each scored title. Logic follows the MSc study's verify.py (pre-existing): Semantic Scholar title
match, similarity >= 0.90 after normalising, failed lookups never cached. Misses get a second look on
Crossref and OpenAlex (recheck.py).

Labels: "verified_s2", "found_elsewhere", "unresolved". A title whose lookup failed has no label yet and is
retried on the next run. "unresolved" never means "does not exist".
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

import recheck
from common import norm

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "audit-study/1.0"}


def s2_lookup(title):
    url = ("https://api.semanticscholar.org/graph/v1/paper/search/match?"
           + urllib.parse.urlencode({"query": title, "fields": "title,year"}))
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                d = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                body = e.read().decode("utf-8", "replace").lower()
                if "not found" in body:
                    return {"matched": None, "ratio": 0.0, "status": "no_match"}
            time.sleep(5 * (attempt + 1))
            continue
        except Exception:
            time.sleep(5 * (attempt + 1))
            continue
        if "data" not in d:
            if "not found" in str(d.get("error", "")).lower():
                return {"matched": None, "ratio": 0.0, "status": "no_match"}
            time.sleep(5 * (attempt + 1))
            continue
        best = {"matched": None, "ratio": 0.0, "status": "ok"}
        for p in d["data"]:
            ratio = SequenceMatcher(None, norm(title), norm(p.get("title") or "")).ratio()
            if ratio > best["ratio"]:
                best.update(matched=p.get("title"), ratio=round(ratio, 3))
        return best
    return {"matched": None, "ratio": 0.0, "status": "error"}


class Labeller:
    """Caches: data/s2_cache.json (new lookups, merged over the pre-existing cache) and
    data/recheck_cache.json. Errors are never cached."""

    def __init__(self, cfg, s2=s2_lookup, sources=None, pause=1.1, data_dir=None):
        self.threshold = cfg["match_threshold"]
        self.s2 = s2
        self.sources = sources if sources is not None else recheck.SOURCES
        self.pause = pause
        data = Path(data_dir) if data_dir else ROOT / "data"
        self.s2_path = data / "s2_cache.json"
        self.rc_path = data / "recheck_cache.json"
        pre = ROOT / cfg["s2_cache_preexisting"]
        self.s2_cache = json.loads(pre.read_text("utf-8")) if pre.exists() else {}
        if self.s2_path.exists():
            self.s2_cache.update(json.loads(self.s2_path.read_text("utf-8")))
        self.new_s2 = json.loads(self.s2_path.read_text("utf-8")) if self.s2_path.exists() else {}
        self.rc_cache = json.loads(self.rc_path.read_text("utf-8")) if self.rc_path.exists() else {}

    def _save(self):
        self.s2_path.parent.mkdir(exist_ok=True)
        self.s2_path.write_text(json.dumps(self.new_s2, ensure_ascii=False), "utf-8")
        self.rc_path.write_text(json.dumps(self.rc_cache, ensure_ascii=False), "utf-8")

    def label(self, title, lookup=True):
        """Return (label or None, matched_record or None). With lookup=False, use caches only."""
        s2 = self.s2_cache.get(title)
        if s2 is None:
            if not lookup:
                return None, None
            s2 = self.s2(title)
            time.sleep(self.pause)
            if s2["status"] == "error":
                return None, None
            self.s2_cache[title] = self.new_s2[title] = s2
            self._save()
        if s2.get("ratio", 0) >= self.threshold:
            return "verified_s2", s2.get("matched")
        rc = self.rc_cache.get(title)
        if rc is None:
            if not lookup:
                return None, None
            per = {}
            for name, fn in self.sources.items():
                try:
                    per[name] = recheck.best(title, fn(title))
                except Exception as e:
                    per[name] = {"error": type(e).__name__}
                time.sleep(self.pause)
            status = recheck.classify(per, self.threshold)
            if status == "lookup_error":
                return None, None
            rc = {"status": status, "sources": per}
            self.rc_cache[title] = rc
            self._save()
        if rc["status"] == "found_elsewhere":
            hit = max((v for v in rc["sources"].values() if "ratio" in v), key=lambda v: v["ratio"])
            return "found_elsewhere", hit.get("matched")
        return "unresolved", None
