"""Offline checks on synthetic data only. No model and no network is touched.
Run: python tests/test_all.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

FAILS = []


def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        FAILS.append(name)


from common import norm, read_jsonl
from parse import parse, p_exists
import sample
import collect
import recheck
import analyze

CFG = {"per_cell": 4, "n_controls": 3, "topic_cap": 1, "sample_seed": 7, "order_seed": 8,
       "bootstrap_seed": 9, "bootstrap_n": 400, "match_threshold": 0.90, "temperature": 0,
       "gen_seed": 1, "max_tokens": 100, "judges": {"J": {"backend": "fake", "model": "fake-1"}},
       "primary_judge": "J", "prompts": "prompts.json"}

# ---------- parse ----------
p = parse("Some thoughts.\nEXISTS: yes\nCONFIDENCE: 85")
check("parse: plain reply", p["ok"] and p["exists"] == "yes" and p["confidence"] == 85)
p = parse("**EXISTS:** Uncertain\n**CONFIDENCE:** 40")
check("parse: markdown and capitals", p["ok"] and p["exists"] == "uncertain" and p["confidence"] == 40)
check("parse: missing confidence is not ok", not parse("EXISTS: no")["ok"])
check("parse: confidence above 100 is not ok", not parse("EXISTS: no\nCONFIDENCE: 150")["ok"])
p = parse("EXISTS: yes\nActually...\nEXISTS: no\nCONFIDENCE: 60")
check("parse: two different answers is a contradiction, not a guess", not p["ok"] and p["contradictory"])
check("parse: empty reply is not ok", not parse("")["ok"] and not parse(None)["ok"])
check("parse: the word 'exists' in prose is not an answer", not parse("I think it exists: yes maybe")["ok"])
check("p_exists: yes 80 -> 0.8", p_exists({"ok": True, "exists": "yes", "confidence": 80}) == 0.8)
check("p_exists: no 80 -> 0.2", abs(p_exists({"ok": True, "exists": "no", "confidence": 80}) - 0.2) < 1e-9)
check("p_exists: uncertain -> 0.5", p_exists({"ok": True, "exists": "uncertain", "confidence": 10}) == 0.5)
check("p_exists: unparsed -> None", p_exists({"ok": False}) is None)

# ---------- sample ----------
def corpus(gen, topics=6, per=3):
    rows = []
    for t in range(topics):
        for i in range(per):
            rows.append({"title": f"{gen} real paper {t}-{i}", "topic": f"topic{t}", "real": True})
            rows.append({"title": f"{gen} invented paper {t}-{i}", "topic": f"topic{t}", "real": False})
    return rows

corp = {"A": corpus("A"), "B": corpus("B")}
controls = [{"title": f"Control paper {i}", "topic": f"topic{i % 6}", "source_url": "u"} for i in range(5)]
items, log = sample.build(corp, controls, CFG)
cells = {}
for it in items:
    cells.setdefault((it["origin"], it["auto_label"]), []).append(it)
check("sample: every generator cell has per_cell items",
      all(len(cells[(g, l)]) == 4 for g in "AB" for l in ("matched", "unmatched")))
check("sample: controls drawn", len(cells[("external", "control_real")]) == 3)
check("sample: labels follow the corpus verdict",
      all(("real" in it["title"]) == (it["auto_label"] == "matched") for it in items if it["origin"] in "AB"))
check("sample: titles unique after normalisation", len({norm(i["title"]) for i in items}) == len(items))
check("sample: topic cap respected",
      all(max(sum(i["topic"] == t for i in c) for t in {i["topic"] for i in c}) <= 1 for c in cells.values() if c[0]["origin"] != "external"))
check("sample: ids unique", len({i["id"] for i in items}) == len(items))
items2, _ = sample.build(corp, controls, CFG)
check("sample: same seed gives the same sample", items == items2)
items3, _ = sample.build(corp, controls, dict(CFG, sample_seed=99))
check("sample: different seed gives a different sample", [i["title"] for i in items3] != [i["title"] for i in items])

# shortfall rule: 2 topics x 3 titles, need 4 with cap 1 -> the cap must rise to 2, and it is logged
small = {"A": corpus("A", topics=2, per=3)}
it_s, log_s = sample.build(small, [], CFG)
check("sample: cap is raised when a cell cannot be filled",
      log_s[0]["picked"] == 4 and log_s[0]["cap_used"] == 2)
# impossible cell: only 2 candidates, need 4 -> returns 2, never invents
tiny = {"A": corpus("A", topics=1, per=2)}
it_t, log_t = sample.build(tiny, [], CFG)
check("sample: an unfillable cell returns the shortfall", log_t[0]["picked"] == 2)
# a title two generators both wrote is used once
dup = {"A": [{"title": "Same Title!", "topic": "t0", "real": True}],
       "B": [{"title": "same title", "topic": "t0", "real": True}]}
it_d, _ = sample.build(dup, [], CFG)
check("sample: duplicate title across generators is used once", len(it_d) == 1)

# scarce-first: B has only 4 unique real titles, all shared with A (which has plenty). B must still get its 4.
scarce = {"A": corpus("A") + [{"title": f"Shared famous paper {i}", "topic": f"topic{i}", "real": True} for i in range(4)],
          "B": [{"title": f"shared famous paper {i}", "topic": f"topic{i}", "real": True} for i in range(4)] * 3}
it_sc, log_sc = sample.build(scarce, [], CFG)
b_cell = [i for i in it_sc if i["origin"] == "B" and i["auto_label"] == "matched"]
a_cell = [i for i in it_sc if i["origin"] == "A" and i["auto_label"] == "matched"]
check("sample: the scarcest cell is filled first", len(b_cell) == 4 and len(a_cell) == 4)
check("sample: repeated titles in one corpus count once", next(c for c in log_sc if c["cell"] == "B/matched")["unique"] == 4)

# ---------- collect (fake backend) ----------
PROMPTS = {"system": "S", "initial": "Title: {title}", "neutral": "again", "challenge": "could not find"}
calls = []


def fake(backend, model, msgs, cfg):
    calls.append(msgs)
    branch = {2: "initial", 4: "follow"}[len(msgs)]
    if branch == "initial":
        return {"text": f"reply to {msgs[1]['content']}\nEXISTS: yes\nCONFIDENCE: 90"}
    ans = "no" if msgs[-1]["content"] == "could not find" else "yes"
    return {"text": f"EXISTS: {ans}\nCONFIDENCE: 70"}


tmp = Path(tempfile.mkdtemp()) / "r.jsonl"
few = items[:3]
n = collect.run(few, CFG["judges"], PROMPTS, CFG, out=tmp, call=fake)
rows = read_jsonl(tmp)
check("collect: three replies per item", n == 9 and len(rows) == 9)
init = {r["item_id"]: r for r in rows if r["branch"] == "initial"}
forks = [r for r in rows if r["branch"] != "initial"]
check("collect: both continuations fork from the same saved initial reply",
      all(r["messages"][2]["content"] == init[r["item_id"]]["text"] for r in forks))
check("collect: initial context is fresh (system + one user turn)",
      all(len(r["messages"]) == 2 for r in init.values()))
check("collect: the title is in the initial prompt",
      all(it["title"] in init[it["id"]]["messages"][1]["content"] for it in few))
check("collect: replies are parsed as they are saved",
      all(r["parsed"]["ok"] for r in rows))
before = len(calls)
n2 = collect.run(few, CFG["judges"], PROMPTS, CFG, out=tmp, call=fake)
check("collect: a second run makes no new calls", n2 == 0 and len(calls) == before)
tmp2 = Path(tempfile.mkdtemp()) / "r.jsonl"
collect.run(few, CFG["judges"], PROMPTS, CFG, out=tmp2, call=fake, limit=4)
check("collect: limit stops mid-run", len(read_jsonl(tmp2)) == 4)
collect.run(few, CFG["judges"], PROMPTS, CFG, out=tmp2, call=fake)
r2 = read_jsonl(tmp2)
check("collect: resume completes without duplicates",
      len(r2) == 9 and len({(r["item_id"], r["branch"]) for r in r2}) == 9)
for name, cfg_bad in (("DRAFT prompts", {"prompts": "prompts.DRAFT.json"}),):
    try:
        collect.guard(cfg_bad)
        check(f"collect: guard refuses {name}", False)
    except SystemExit:
        check(f"collect: guard refuses {name}", True)

# ---------- recheck ----------
b = recheck.best("Attention Is All You Need", ["attention is all you need.", "Something else"])
check("recheck: punctuation and case do not matter", b["ratio"] == 1.0)
check("recheck: unrelated title scores low", recheck.best("Attention Is All You Need", ["Deep residual learning"])["ratio"] < 0.9)
check("recheck: hit in one source is found_elsewhere",
      recheck.classify({"a": {"ratio": 0.95}, "b": {"ratio": 0.2}}, 0.9) == "found_elsewhere")
check("recheck: no hit is unresolved", recheck.classify({"a": {"ratio": 0.5}, "b": {"ratio": 0.2}}, 0.9) == "unresolved")
check("recheck: an error is never called unresolved",
      recheck.classify({"a": {"ratio": 0.5}, "b": {"error": "URLError"}}, 0.9) == "lookup_error")
check("recheck: a hit beats an error",
      recheck.classify({"a": {"ratio": 0.95}, "b": {"error": "URLError"}}, 0.9) == "found_elsewhere")

# ---------- analyze ----------
def P(e, c=80):
    return {"ok": True, "exists": e, "confidence": c, "contradictory": False}


BAD = {"ok": False, "exists": None, "confidence": None, "contradictory": False}
its = [{"id": f"R{i}", "topic": f"t{i % 5}", "origin": "A", "auto_label": "matched"} for i in range(10)]
its += [{"id": f"U{i}", "topic": f"t{i % 5}", "origin": "A", "auto_label": "unmatched"} for i in range(10)]
rc = {f"U{i}": {"status": "unresolved"} for i in range(8)}
rc["U8"] = {"status": "found_elsewhere"}
rc["U9"] = {"status": "lookup_error"}
labels = analyze.final_labels(its, rc)
check("analyze: matched -> verified_real", labels["R0"] == "verified_real")
check("analyze: unmatched + not found -> unresolved", labels["U0"] == "unresolved")
check("analyze: found elsewhere is kept apart", labels["U8"] == "found_elsewhere")
check("analyze: lookup error gets no label", "U9" not in labels)

rows = []
def add(i, ini, neu, cha):
    for b, v in (("initial", ini), ("neutral", neu), ("challenge", cha)):
        rows.append({"judge": "J", "item_id": i, "branch": b, "parsed": v})

# 10 real: R0-R7 endorsed. Challenge: R0-R3 denied (4/8). Neutral: R0 denied (1/8). R8 initially 'no'. R9 unparsed.
for i in range(8):
    add(f"R{i}", P("yes", 90), P("no") if i == 0 else P("yes"), P("no") if i < 4 else P("uncertain") if i == 4 else P("yes"))
add("R8", P("no", 60), P("no"), P("no"))
add("R9", P("yes"), BAD, P("no"))
# 8 unresolved, all endorsed at 60; challenge keeps 2 of 8, neutral keeps 8 of 8
for i in range(8):
    add(f"U{i}", P("yes", 60), P("yes"), P("yes") if i < 2 else P("no"))
res = analyze.analyse(its, labels, rows, CFG)["J"]
pr = res["primary_real_denied"]
check("analyze: primary denominator = verified, endorsed, fully parsed", pr["n"] == 8)
check("analyze: primary rates and difference", pr["challenge_rate"] == 0.5 and pr["neutral_rate"] == 0.125 and pr["diff"] == 0.375)
check("analyze: CI brackets the estimate", pr["ci95"][0] <= pr["diff"] <= pr["ci95"][1])
check("analyze: uncertainty is not counted as denial", res["real_moved_to_uncertain"]["diff"] == 0.125)
ue = res["unresolved_still_endorsed"]
check("analyze: unresolved still endorsed", ue["n"] == 8 and ue["challenge_rate"] == 0.25 and ue["diff"] == -0.75)
check("analyze: unparsed triple is counted, not dropped silently", res["unparsed_triples"]["verified_real"] == 1)
# AUROC: verified initial p = .9 x9 (R0-R7,R9) and .4 (R8); unresolved p = .6 x8 -> 9 of 10 verified score higher
check("analyze: AUROC on known scores", abs(res["auroc_initial_verified_vs_unresolved"] - 0.9) < 1e-9)
check("analyze: found_elsewhere and error items are in no group", res["n_scored"] == {"verified_real": 10, "unresolved": 8})
check("auroc: ties count half", analyze.auroc([0.5], [0.5]) == 0.5)
check("auroc: empty group -> None", analyze.auroc([], [0.5]) is None)
check("bootstrap: one topic -> no interval", analyze.cluster_bootstrap([{"topic": "t", "neutral": "yes", "challenge": "no"}], lambda x: 1.0, 50, 1) is None)
same = [{"topic": f"t{i}", "neutral": "yes", "challenge": "no"} for i in range(6)]
check("bootstrap: constant data gives a zero-width interval",
      analyze.cluster_bootstrap(same, lambda x: analyze.paired_diff(x, "no"), 200, 1) == [1.0, 1.0])
check("paired_diff: empty -> None", analyze.paired_diff([], "no") is None)

print(f"\n{'RED' if FAILS else 'GREEN'}: {len(FAILS)} failing")
sys.exit(1 if FAILS else 0)
