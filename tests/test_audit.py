"""Offline checks for the announced-audit design. Synthetic data only: no model, no network.
Run: python tests/test_audit.py
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


import design
import lists
import llm
import run
import analysis
from verify import Labeller

PROMPTS = json.loads((design.ROOT / "prompts.DRAFT.json").read_text("utf-8"))
CFG = design.load_config()
TOPICS = [{"topic": f"topic {i}", "papers": 10 * i} for i in range(1, 6)]

# ---------- design ----------
m = design.manifest(CFG, TOPICS)
g = [x for x in m if x["arm"] == "gptoss"]
l = [x for x in m if x["arm"] == "llama"]
check("manifest: gpt-oss = topics x 4 conditions x 2 pairs + 2 A/A runs", len(g) == 5 * 4 * 2 + 5 * 2)
check("manifest: llama = topics x 4 conditions x pair 1", len(l) == 5 * 4 and {x["pair"] for x in l} == {"1"})
check("manifest: ids unique", len({x["id"] for x in m}) == len(m))
check("manifest: seeds distinct", len({x["seed"] for x in m}) == len(m))
check("manifest: deterministic", m == design.manifest(CFG, TOPICS))
blocks_ok = True
seq = [x for x in g]
pos = 0
while pos < len(seq):
    x = seq[pos]
    if x["condition"] == "BASE":
        pos += 1
        continue
    blk = seq[pos:pos + 4]
    if {y["condition"] for y in blk} != set(design.CONDITIONS) or len({(y["topic"], y["pair"]) for y in blk}) != 1:
        blocks_ok = False
        break
    pos += 4
check("manifest: each topic x pair block holds all four conditions together", blocks_ok)
check("manifest: condition order varies between blocks",
      len({tuple(y["condition"] for y in seq[i:i + 4]) for i in range(len(seq)) if seq[i]["condition"] != "BASE"}) > 1)

# ---------- collection priority (FREEZE section 5) ----------
for arm in ("gptoss", "llama"):
    seq_arm = [x for x in m if x["arm"] == arm]
    first_base = next((i for i, x in enumerate(seq_arm) if x["condition"] == "BASE"), len(seq_arm))
    check(f"priority: {arm} collects every main condition before any A/A repeat",
          all(x["condition"] == "BASE" for x in seq_arm[first_base:]))
check("priority: both notice wordings are main items (never in the droppable tail)",
      {x["pair"] for x in g if x["condition"] != "BASE"} == {"1", "2"})
order = run.plan_order(CFG, "gptoss", main_done=False, stage2_done=False)
check("priority: main conditions first", order == ["main"])
check("priority: then stage two, before the A/A repeats",
      run.plan_order(CFG, "gptoss", main_done=True, stage2_done=False) == ["stage2"])
check("priority: A/A repeats only after stage two is complete",
      run.plan_order(CFG, "gptoss", main_done=True, stage2_done=True) == ["aa"])
check("priority: an arm without stage two or repeats stops after the main conditions",
      run.plan_order(CFG, "llama", main_done=True, stage2_done=True) == [])

base = design.user_prompt(PROMPTS, "graph neural networks", "AA1", "BASE")
check("prompt: BASE is the study's request unchanged",
      base == PROMPTS["base"].format(topic="graph neural networks") and "Accuracy" not in base)
for c, (notice, qty) in design.CONDITIONS.items():
    for pair in ("1", "2"):
        p = design.user_prompt(PROMPTS, "graph neural networks", pair, c)
        ok = (p.startswith(base) and PROMPTS["accuracy"] in p and PROMPTS["notices"][pair][notice] in p
              and PROMPTS["quantity"][qty] in p)
        other = "audit" if notice == "archive" else "archive"
        ok = ok and PROMPTS["notices"][pair][other] not in p
        if not ok:
            check(f"prompt: {c} pair {pair} has exactly its parts", False)
check("prompt: every condition = base + accuracy + its notice + its quantity line", not [f for f in FAILS if f.startswith("prompt:")])
check("prompt: no prompt names the database",
      all("semantic scholar" not in design.user_prompt(PROMPTS, "x", "1", c).lower() for c in design.CONDITIONS))
for a, b in (("archive", "audit"),):
    for pair in ("1", "2"):
        check(f"prompt: pair {pair} notices have equal word counts",
              len(PROMPTS["notices"][pair][a].split()) == len(PROMPTS["notices"][pair][b].split()))
check("prompt: quantity lines have equal word counts",
      len(PROMPTS["quantity"]["ten"].split()) == len(PROMPTS["quantity"]["fewer"].split()))
try:
    design.guard(dict(CFG, prompts="prompts.DRAFT.json"))
    check("guard: refuses DRAFT prompts", False)
except SystemExit:
    check("guard: refuses DRAFT prompts", True)

# ---------- lists ----------
txt = ("4. Graph Attention Networks\n5. Semi-Supervised Classification with Graph Convolutional Networks\n"
       "6. Attention Is All You Need\n7. graph attention networks\nSome prose\n8) Inductive Representation Learning on Large Graphs")
t, rep = lists.scored_titles(txt)
check("lists: seeds dropped, repeats dropped and counted, non-numbered lines ignored",
      t == ["Graph Attention Networks", "Semi-Supervised Classification with Graph Convolutional Networks",
            "Inductive Representation Learning on Large Graphs"] and rep == 1)
many = "\n".join(f"{i}. Paper number {i}" for i in range(4, 20))
check("lists: at most ten scored", len(lists.scored_titles(many)[0]) == 10)
check("lists: empty reply -> nothing", lists.scored_titles("")[0] == [] and lists.scored_titles(None)[0] == [])
check("lists: numbered items keep their numbers", lists.numbered_items(txt)[0] == (4, "Graph Attention Networks"))

# ---------- llm ----------
check("llm: NVIDIA endpoint uses its own key name",
      llm.ENDPOINTS["nim"] == ("https://integrate.api.nvidia.com/v1/chat/completions", "NVIDIA_API_KEY")
      and "nim" in llm.BACKENDS)
check("llm: Groq wait '1m26.4s' parsed", abs(llm._wait_seconds({"x-ratelimit-reset-requests": "1m26.4s"}) - 86.4) < 1e-6)
check("llm: retry-after seconds parsed", llm._wait_seconds({"retry-after": "7"}) == 7.0)

# ---------- collect ----------
calls = []


def fake(backend, model, msgs, temperature, seed, max_tokens):
    calls.append((backend, model, seed, temperature, max_tokens, msgs[-1]["content"]))
    return {"text": "4. Real Paper A\n5. Made Up Paper B", "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "finish": "stop"}


tmp = Path(tempfile.mkdtemp())
out = tmp / "gen.jsonl"
made, why = run.collect(CFG, PROMPTS, "gptoss", m, fake, out, deadline=1e18)
rows = run.read_jsonl(out)
check("collect: all gpt-oss items, only gpt-oss", made == len(g) and why == "done" and all(r["arm"] == "gptoss" for r in rows))
check("collect: uses the arm's backend, model, temperature and per-call seed",
      calls[0][:2] == ("groq", "openai/gpt-oss-120b") and calls[0][3] == CFG["temperature"]
      and calls[0][2] == g[0]["seed"])
check("collect: titles parsed on save", rows[0]["titles"] == ["Real Paper A", "Made Up Paper B"])
n = len(calls)
check("collect: second run makes no calls", run.collect(CFG, PROMPTS, "gptoss", m, fake, out, 1e18)[0] == 0 and len(calls) == n)


def limited(*a):
    raise llm.DailyLimit("quota")


out2 = tmp / "gen2.jsonl"
run.collect(CFG, PROMPTS, "gptoss", m, fake, out2, 1e18, limit=3)
made2, why2 = run.collect(CFG, PROMPTS, "gptoss", m, limited, out2, 1e18)
check("collect: daily limit stops cleanly, keeps finished rows", made2 == 0 and why2.startswith("daily limit")
      and len(run.read_jsonl(out2)) == 3)
check("collect: deadline stops before calling", run.collect(CFG, PROMPTS, "gptoss", m, fake, tmp / "g3.jsonl", 0)[1] == "time")

# ---------- retries and attempt log (FREEZE section 6) ----------
class Seq:
    """Returns or raises the given outcomes in order."""
    def __init__(self, outcomes):
        self.outcomes, self.n = list(outcomes), 0
    def __call__(self, *a):
        o = self.outcomes[min(self.n, len(self.outcomes) - 1)]
        self.n += 1
        if isinstance(o, Exception):
            raise o
        return o

OK = {"text": "4. Real Paper A", "usage": {}, "finish": "stop"}
one = [x for x in m if x["arm"] == "gptoss"][:1]
three = [x for x in m if x["arm"] == "gptoss"][:5]
nosleep = lambda s: None

out_r = tmp / "retry.jsonl"; log_r = tmp / "retry_attempts.jsonl"
made_r, _ = run.collect(CFG, PROMPTS, "gptoss", one, Seq([llm.Transient("timeout"), llm.Transient("HTTP 503"), OK]),
                        out_r, 1e18, sleep=nosleep, attempts_log=log_r)
att = run.read_jsonl(log_r)
check("retry: transient errors retried, then the reply is saved", made_r == 1 and len(run.read_jsonl(out_r)) == 1)
check("retry: every attempt logged with time and outcome",
      [a["outcome"] for a in att] == ["timeout", "HTTP 503", "ok"] and all(a.get("utc") and a["id"] == one[0]["id"] for a in att))

out_f = tmp / "fail.jsonl"; log_f = tmp / "fail_attempts.jsonl"
seq = Seq([llm.Transient("timeout")] * 4 + [OK] * 10)
made_f, why_f = run.collect(CFG, PROMPTS, "gptoss", three[:2], seq, out_f, 1e18, sleep=nosleep, attempts_log=log_f)
att = run.read_jsonl(log_f)
check("retry: at most 3 retries (4 attempts), then logged as failed and skipped",
      [a["outcome"] for a in att][:5] == ["timeout"] * 4 + ["failed"] and seq.n == 5)
check("retry: a failed call is not saved as data; the next item still runs",
      [r["id"] for r in run.read_jsonl(out_f)] == [three[1]["id"]] and made_f == 1)
made_again, _ = run.collect(CFG, PROMPTS, "gptoss", three[:2], Seq([OK]), out_f, 1e18, sleep=nosleep, attempts_log=log_f)
check("retry: the failed call is picked up by the next run", made_again == 1 and len(run.read_jsonl(out_f)) == 2)

out_s = tmp / "stop.jsonl"
made_s, why_s = run.collect(CFG, PROMPTS, "gptoss", three, Seq([llm.Transient("HTTP 502")]), out_s, 1e18,
                            sleep=nosleep, attempts_log=tmp / "stop_attempts.jsonl")
check("retry: three failed calls in a row stop the run (service down)", made_s == 0 and why_s.startswith("stopped"))

waits = []
run.collect(CFG, PROMPTS, "gptoss", one, Seq([llm.Transient("HTTP 429", wait=7.0), OK]), tmp / "w.jsonl", 1e18,
            sleep=waits.append, attempts_log=tmp / "w_attempts.jsonl")
check("retry: a short rate-limit waits as long as Groq asks", waits == [7.0])

made_d, why_d = run.collect(CFG, PROMPTS, "gptoss", one, Seq([llm.DailyLimit("quota")]), tmp / "d.jsonl", 1e18,
                            sleep=nosleep, attempts_log=tmp / "d_attempts.jsonl")
check("retry: daily quota is not retried; it stops the run and is logged",
      why_d.startswith("daily limit") and run.read_jsonl(tmp / "d_attempts.jsonl")[0]["outcome"].startswith("daily limit"))
try:
    run.collect(CFG, PROMPTS, "gptoss", one, Seq([ValueError("HTTP 401 bad key")]), tmp / "x.jsonl", 1e18,
                sleep=nosleep, attempts_log=tmp / "x_attempts.jsonl")
    check("retry: other errors (bad key, bad request) are not retried and stop the run", False)
except ValueError:
    check("retry: other errors (bad key, bad request) are not retried and stop the run",
          run.read_jsonl(tmp / "x_attempts.jsonl")[0]["outcome"].startswith("error"))

# ---------- two runners sharing the gpt-oss calls ----------
seq10 = list(range(10))
check("shard: the two shares are disjoint and cover everything",
      run.shard_filter(seq10, (1, 2)) == [0, 2, 4, 6, 8] and run.shard_filter(seq10, (2, 2)) == [1, 3, 5, 7, 9])
check("shard: 1/1 is everything", run.shard_filter(seq10, (1, 1)) == seq10)
outA, outB = tmp / "gA.jsonl", tmp / "gB.jsonl"
itemsg = [x for x in m if x["arm"] == "gptoss"][:6]
run.collect(CFG, PROMPTS, "gptoss", run.shard_filter(itemsg, (1, 2)), fake, outA, 1e18, attempts_log=tmp / "aA.jsonl")
run.collect(CFG, PROMPTS, "gptoss", run.shard_filter(itemsg, (2, 2)), fake, outB, 1e18, attempts_log=tmp / "aB.jsonl")
idsA = {r["id"] for r in run.read_jsonl(outA)}
idsB = {r["id"] for r in run.read_jsonl(outB)}
check("shard: two runners collect every item exactly once", not (idsA & idsB) and len(idsA | idsB) == 6)
n_before = len(calls)
run.collect(CFG, PROMPTS, "gptoss", itemsg, fake, tmp / "gC.jsonl", 1e18, attempts_log=tmp / "aC.jsonl",
            also_done=idsA | idsB)
check("shard: ids collected by any runner are skipped", len(calls) == n_before)

s2_calls = []


def fake_s2(title):
    s2_calls.append(title)
    if title == "Broken Lookup":
        return {"matched": None, "ratio": 0.0, "status": "error"}
    if title.startswith("Real"):
        return {"matched": title, "ratio": 1.0, "status": "ok"}
    return {"matched": None, "ratio": 0.0, "status": "no_match"}


def fake_src(title):
    return ["Elsewhere Paper C"] if title == "Elsewhere Paper C" else ["unrelated"]


lab = Labeller(dict(CFG, s2_cache_preexisting="nope.json", s2_live=True), s2=fake_s2, sources={"x": fake_src}, pause=0,
               data_dir=tmp / "data")
check("label: S2 match -> verified_s2", lab.label("Real Paper A")[0] == "verified_s2")
check("label: S2 miss, found on another index -> found_elsewhere", lab.label("Elsewhere Paper C")[0] == "found_elsewhere")
check("label: found nowhere -> unresolved", lab.label("Made Up Paper B")[0] == "unresolved")
check("label: failed lookup -> no label, not cached", lab.label("Broken Lookup")[0] is None
      and "Broken Lookup" not in json.loads((tmp / "data" / "s2_cache.json").read_text("utf-8")))
k = len(s2_calls)
lab.label("Real Paper A")
check("label: cached titles are not looked up again", len(s2_calls) == k)
check("label: cache-only mode never calls out", lab.label("Never Seen", lookup=False) == (None, None) and len(s2_calls) == k)
lab2 = Labeller(dict(CFG, s2_cache_preexisting="nope.json", s2_live=True), s2=fake_s2, sources={"x": fake_src}, pause=0,
                data_dir=tmp / "data")
check("label: caches persist across runs", lab2.label("Made Up Paper B", lookup=False)[0] == "unresolved")
check("label_all: counts what is still unlabelled",
      run.label_all(lab, [{"titles": ["Real Paper A", "Broken Lookup"]}], 1e18) == 1)

calls_s2 = []
def always_fail(title):
    calls_s2.append(title)
    return {"matched": None, "ratio": 0.0, "status": "error"}
lab_down = Labeller(dict(CFG, s2_cache_preexisting="nope.json", s2_live=True), s2=always_fail, sources={"x": fake_src}, pause=0,
                    data_dir=tmp / "data_down")
left = run.label_all(lab_down, [{"titles": [f"Title {i}" for i in range(20)]}], 1e18)
check("label_all: stops calling a service that keeps failing", left == 20 and len(calls_s2) == 5)
check("config: collection cannot start before the sprint kickoff", CFG["collect_not_before_utc"] == "2026-11-13T14:15:00Z")

# ---------- deviation 3: Crossref and OpenAlex, Semantic Scholar from cache only ----------
s2_calls3 = []
def s2_should_not_run(t):
    s2_calls3.append(t)
    return {"matched": t, "ratio": 1.0, "status": "ok"}
lab3 = Labeller(dict(CFG, s2_cache_preexisting="nope.json", s2_live=False), s2=s2_should_not_run,
                sources={"x": fake_src}, pause=0, data_dir=tmp / "data3")
check("dev3: no live Semantic Scholar lookups", lab3.label("Real Paper Z")[0] == "unresolved" and s2_calls3 == [])
check("dev3: found on Crossref/OpenAlex -> found_elsewhere", lab3.label("Elsewhere Paper C")[0] == "found_elsewhere")
lab3.s2_cache["Cached Real"] = {"matched": "Cached Real", "ratio": 1.0, "status": "ok"}
check("dev3: a cached Semantic Scholar match is still used", lab3.label("Cached Real")[0] == "verified_s2")
lab4 = Labeller(dict(CFG, s2_cache_preexisting="nope.json", s2_live=False), s2=s2_should_not_run,
                sources={"x": fake_src}, pause=0, data_dir=tmp / "data4")
par_rows = [{"titles": ["Elsewhere Paper C", "Made Up Paper B", "Another Fake", "Elsewhere Paper C"]}]
left = run.label_parallel(lab4, par_rows, 1e18, workers=3)
check("dev3: parallel labelling labels every title once", left == 0 and
      [lab4.label(t, lookup=False)[0] for t in ("Elsewhere Paper C", "Made Up Paper B", "Another Fake")]
      == ["found_elsewhere", "unresolved", "unresolved"])
check("dev3: parallel labels persist", Labeller(dict(CFG, s2_cache_preexisting="nope.json", s2_live=False),
      sources={"x": fake_src}, pause=0, data_dir=tmp / "data4").label("Another Fake", lookup=False)[0] == "unresolved")

# ---------- stage two ----------
row = {"id": "gptoss|t|1|P10", "messages": [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}],
       "text": "4. Real Paper A\n5. Made Up Paper B\n6. Elsewhere Paper C"}
neutral = run.stage2_messages(PROMPTS, row, "neutral", lab)
receipts = run.stage2_messages(PROMPTS, row, "receipts", lab)
audit = run.stage2_messages(PROMPTS, row, "audit", lab)
check("stage2: every branch forks from the same saved list",
      all(x[:3] == row["messages"] + [{"role": "assistant", "content": row["text"]}] for x in (neutral, audit, receipts)))
check("stage2: neutral has no audit notice", PROMPTS["stage2"]["audit_notice"] not in neutral[-1]["content"])
check("stage2: audit branch adds only the notice",
      audit[-1]["content"] == PROMPTS["stage2"]["audit_notice"] + "\n\n" + PROMPTS["stage2"]["instruction"])
rc = receipts[-1]["content"]
check("stage2: receipts report found and not found per item",
      "Item 4: a matching published record was found." in rc and "Item 5: no matching" in rc
      and "Item 6: a matching published record was found." in rc)
check("stage2: unlabelled item -> wait (None)",
      run.stage2_messages(PROMPTS, dict(row, text="4. Never Looked Up Title"), "receipts", lab) is None)
d = run.parse_decisions("4. KEEP\n5 - WITHDRAW\nItem 6: **keep**\n2. WITHDRAW\n14. KEEP")
check("stage2: decisions parsed, out-of-range items ignored", d == {4: "KEEP", 5: "WITHDRAW", 6: "KEEP"})

# ---------- analysis ----------
labels = {"Real 1": ("verified_s2", "Real 1"), "Real 2": ("verified_s2", "Real 2"), "Else": ("found_elsewhere", "Else"),
          "Fake": ("unresolved", None), "Fake2": ("unresolved", None)}
lo = lambda t: labels.get(t, (None, None))
s = analysis.score_request({"titles": ["Real 1", "Else", "Fake", "Fake2"]}, lo)
check("score: U, V, given", s == {"U": 2, "V": 2, "given": 4, "s2_unmatched": 3})
check("score: any unlabelled title -> request not scored", analysis.score_request({"titles": ["Real 1", "??"]}, lo) is None)


def mk(topic, pair, cond, titles):
    return {"topic": topic, "pair": pair, "condition": cond, "titles": titles}


rows = []
for i in range(6):
    for pair in ("1", "2"):
        rows.append(mk(f"t{i}", pair, "P10", ["Real 1", "Fake", "Fake2"]))      # U=2
        rows.append(mk(f"t{i}", pair, "A10", ["Real 1", "Real 2", "Fake"]))      # U=1, V=2
        rows.append(mk(f"t{i}", pair, "P<10", ["Real 1"]))
        rows.append(mk(f"t{i}", pair, "A<10", ["Real 1"]))
cfg2 = dict(CFG, arms={"gptoss": dict(CFG["arms"]["gptoss"], stage2=False)}, bootstrap_n=500)
res = analysis.analyse(cfg2, {"gptoss": rows}, lo)["arms"]["gptoss"]
p = res["primary_U_A10_minus_P10"]
check("analysis: primary contrast = -1 unresolved per request", p["mean"] == -1 and p["topics"] == 6)
check("analysis: constant effect -> zero-width interval at -1", p["ci"] == [-1, -1])
check("analysis: guardrail V contrast = +1", res["guardrail_V_A10_minus_P10"]["mean"] == 1)
check("analysis: verdict 'works'", res["verdict"] == "works")
rows_less = [dict(r, titles=["Fake"]) if r["condition"] == "A10" else r for r in rows]
check("analysis: fewer unresolved but fewer real papers -> 'works by citing less'",
      analysis.analyse(cfg2, {"gptoss": rows_less}, lo)["arms"]["gptoss"]["verdict"] == "works by citing less")
rows_same = [dict(r, titles=["Real 1", "Fake", "Fake2"]) if r["condition"] == "A10" else r for r in rows]
check("analysis: identical cells -> 'no meaningful effect'",
      analysis.analyse(cfg2, {"gptoss": rows_same}, lo)["arms"]["gptoss"]["verdict"] == "no meaningful effect")
rows_worse = [dict(r, titles=["Fake", "Fake2", "Real 1"]) if r["condition"] == "P10" else
              (dict(r, titles=["Fake", "Fake2", "Fake3"]) if r["condition"] == "A10" else r) for r in rows]
labels["Fake3"] = ("unresolved", None)
check("analysis: more unresolved titles under the audit notice -> 'increases unmatched titles'",
      analysis.analyse(cfg2, {"gptoss": rows_worse}, lo)["arms"]["gptoss"]["verdict"] == "increases unmatched titles")
u = lambda lo_, hi: {"ci": [lo_, hi], "topics": 40, "mean": (lo_ + hi) / 2}
check("verdict (b): clear but small decrease inside +/-0.5 -> 'real but small (decrease)'",
      analysis.verdict(u(-0.3, -0.1), u(-0.28, -0.12), u(-0.1, 0.2), CFG) == "real but small (decrease)")
check("verdict (b): clear but small increase inside +/-0.5 -> 'real but small (increase)'",
      analysis.verdict(u(0.1, 0.3), u(0.12, 0.28), u(-0.1, 0.2), CFG) == "real but small (increase)")
check("verdict: a large clear decrease is still 'works'",
      analysis.verdict(u(-1.5, -0.6), u(-1.4, -0.7), u(-0.2, 0.3), CFG) == "works")
check("verdict: interval crossing zero and wider than the margin -> 'inconclusive'",
      analysis.verdict(u(-0.9, 0.4), u(-0.8, 0.3), u(-0.2, 0.3), CFG) == "inconclusive")
check("analysis: one topic only -> 'not enough data'",
      analysis.analyse(cfg2, {"gptoss": [r for r in rows if r["topic"] == "t0"]}, lo)["arms"]["gptoss"]["verdict"] == "not enough data")
half = [r for r in rows if not (r["pair"] == "2" and r["condition"] == "A10")]
check("analysis: a topic missing one pair still uses the complete pair",
      analysis.analyse(cfg2, {"gptoss": half}, lo)["arms"]["gptoss"]["primary_U_A10_minus_P10"]["topics"] == 6)
check("analysis: interaction computed",
      res["U_interaction"]["mean"] == ((0 - 0) - (1 - 2)))

# ---------- audit correction (FREEZE section 12) ----------
counts = {"A10": {"unres_n": 25, "unres_real": 5, "match_n": 30, "match_fake": 3},
          "P10": {"unres_n": 25, "unres_real": 0, "match_n": 30, "match_fake": 0},
          "A<10": {"unres_n": 10, "unres_real": 5, "match_n": 10, "match_fake": 0}}
rates = analysis.audit_rates(counts, min_n=20)
check("audit: p and q per condition", rates["A10"] == {"p": 0.2, "q": 0.1} and rates["P10"] == {"p": 0.0, "q": 0.0})
pooled_p = (5 + 0 + 5) / (25 + 25 + 10)
pooled_q = (3 + 0 + 0) / (30 + 30 + 10)
check("audit: fewer than 20 audited titles in a label -> pooled rate",
      abs(rates["A<10"]["p"] - pooled_p) < 1e-12 and abs(rates["A<10"]["q"] - pooled_q) < 1e-12)
check("audit: a condition with no audit at all uses pooled rates",
      abs(analysis.audit_rates(counts, min_n=20, conditions=["P<10"])["P<10"]["p"] - pooled_p) < 1e-12)
check("audit: corrected U = U(1-p) + M q",
      abs(analysis.corrected_U({"U": 4, "given": 10}, {"p": 0.25, "q": 0.1}) - (4 * 0.75 + 6 * 0.1)) < 1e-12)
res_c = analysis.analyse(cfg2, {"gptoss": rows}, lo,
                         audit_counts={"P10": {"unres_n": 30, "unres_real": 0, "match_n": 30, "match_fake": 0},
                                       "A10": {"unres_n": 30, "unres_real": 0, "match_n": 30, "match_fake": 0},
                                       "P<10": {"unres_n": 30, "unres_real": 0, "match_n": 30, "match_fake": 0},
                                       "A<10": {"unres_n": 30, "unres_real": 0, "match_n": 30, "match_fake": 0}})
pc = res_c["arms"]["gptoss"]["primary_U_corrected"]
check("audit: a perfect audit leaves the primary result unchanged", pc["mean"] == -1)
res_n = analysis.analyse(cfg2, {"gptoss": rows}, lo)
check("audit: without audit data the corrected result is absent, not invented",
      res_n["arms"]["gptoss"]["primary_U_corrected"] is None)

# ---------- collection window (FREEZE section 6) ----------
from datetime import datetime, timezone
at = lambda iso: datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
check("window: closed before the sprint kickoff", run.collection_open(CFG, at("2026-11-13T14:14:59"))[0] is False)
check("window: open after kickoff", run.collection_open(CFG, at("2026-11-13T14:15:00"))[0] is True)
check("window: closed after the cutoff, Sunday 18:00 IST", CFG["collect_cutoff_utc"] == "2026-11-15T12:30:00Z"
      and run.collection_open(CFG, at("2026-11-15T12:30:00"))[0] is False
      and run.collection_open(CFG, at("2026-11-15T12:29:59"))[0] is True)

rows_dup = [{"id": "x", "utc": "2026-11-13T17:05:00", "v": 2}, {"id": "x", "utc": "2026-11-13T17:01:00", "v": 1},
            {"id": "y", "utc": "2026-11-13T17:02:00", "v": 3}]
kept = sorted(run._first_per_id(rows_dup), key=lambda r: r["id"])
check("dedupe: a call collected twice keeps the earlier reply", [r["v"] for r in kept] == [1, 3])

import recheck as _rc
check("dev3b: the second look uses Crossref and arXiv", set(_rc.SOURCES) == {"crossref", "arxiv"})
_waits = []
_rc._ARXIV_LAST[0] = 99.0
_orig = _rc.urllib.request.urlopen


class _R:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Graph  Attention Networks</title></entry></feed>'


_rc.urllib.request.urlopen = lambda *a, **k: _R()
got = _rc.arxiv("Graph Attention Networks", _sleep=_waits.append, _now=lambda: 100.0)
_rc.urllib.request.urlopen = _orig
check("dev3b: arXiv calls are spaced at least 3.1 s apart", abs(_waits[0] - 2.1) < 1e-9 and got == ["Graph Attention Networks"])

print(f"\n{'RED' if FAILS else 'GREEN'}: {len(FAILS)} failing")
sys.exit(1 if FAILS else 0)
