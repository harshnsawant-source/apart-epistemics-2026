"""Draw the evaluation sample. Deterministic: same corpus + same seed -> same manifest.

Cells: for each generator, `per_cell` titles the study's verifier matched and `per_cell` it did not,
plus `n_controls` real papers from an independent source (data/controls.csv: topic,title,source_url).
Titles are unique after normalisation across the whole sample. At most `topic_cap` titles per topic in a
cell; if a cell cannot be filled, the cap is raised by one at a time (the shortfall rule, logged).

Run: python src/sample.py            -> data/manifest.json
"""
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_config, norm, read_jsonl, resolve, sha256_file


def draw_cell(rows, n, cap, rng, taken):
    """rows: [{title, topic}] candidates for one cell. Returns (picked, cap_used)."""
    pool = sorted(rows, key=lambda r: (r["topic"], r["title"]))
    rng.shuffle(pool)
    while True:
        picked, per_topic, seen = [], {}, set(taken)
        for r in pool:
            k = norm(r["title"])
            if not k or k in seen or per_topic.get(r["topic"], 0) >= cap:
                continue
            picked.append(r)
            seen.add(k)
            per_topic[r["topic"]] = per_topic.get(r["topic"], 0) + 1
            if len(picked) == n:
                return picked, cap
        if cap >= len(pool):
            return picked, cap          # corpus exhausted: return the shortfall, never invent items
        cap += 1


def build(corpus, controls, cfg):
    """corpus: {generator: [verdict rows]}; controls: [{title, topic, source_url}]."""
    rng = random.Random(cfg["sample_seed"])
    items, taken, log = [], set(), []
    cells = []
    for gen in sorted(corpus):
        for label, want in (("matched", True), ("unmatched", False)):
            rows = [{"title": r["title"], "topic": r["topic"]} for r in corpus[gen] if bool(r["real"]) is want]
            cells.append((len({norm(r["title"]) for r in rows}), gen, label, rows))
    # Scarcest cell first: a title two generators both wrote goes to the cell with fewer unique titles.
    for unique, gen, label, rows in sorted(cells, key=lambda c: c[:3]):
        picked, cap = draw_cell(rows, cfg["per_cell"], cfg["topic_cap"], rng, taken)
        log.append({"cell": f"{gen}/{label}", "candidates": len(rows), "unique": unique,
                    "picked": len(picked), "cap_used": cap})
        for r in picked:
            taken.add(norm(r["title"]))
            items.append({"title": r["title"], "topic": r["topic"], "origin": gen, "auto_label": label})
    ctrl = [c for c in controls if norm(c["title"]) not in taken]
    ctrl = sorted(ctrl, key=lambda r: (r["topic"], r["title"]))
    rng.shuffle(ctrl)
    for c in ctrl[: cfg["n_controls"]]:
        taken.add(norm(c["title"]))
        items.append({"title": c["title"], "topic": c["topic"], "origin": "external",
                      "auto_label": "control_real", "source_url": c.get("source_url", "")})
    log.append({"cell": "external/control_real", "candidates": len(controls),
                "picked": sum(i["origin"] == "external" for i in items), "cap_used": None})
    for n, it in enumerate(items, 1):
        it["id"] = f"T{n:03d}"
    return items, log


def main():
    cfg = load_config()
    corpus, hashes = {}, {}
    for gen, p in cfg["corpus"].items():
        corpus[gen] = read_jsonl(resolve(p))
        hashes[gen] = sha256_file(resolve(p))
    cpath = resolve(cfg["controls_csv"])
    controls = list(csv.DictReader(cpath.open(encoding="utf-8-sig"))) if cpath.exists() else []
    items, log = build(corpus, controls, cfg)
    out = ROOT / "data" / "manifest.json"
    out.write_text(json.dumps({"seed": cfg["sample_seed"], "corpus_sha256": hashes, "cells": log, "items": items},
                              ensure_ascii=False, indent=1), "utf-8")
    for c in log:
        print(c)
    print(len(items), "items ->", out)


if __name__ == "__main__":
    main()
