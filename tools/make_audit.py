"""Build the blind hand-audit page (FREEZE section 12).

Sample: 200 scored gpt-oss titles from the four main conditions, 25 per condition x label (matched vs unmatched),
drawn with a fixed seed, spread across topics, then shuffled. The first 50 in the shuffled order also get an
on-topic / off-topic question. Condition, label and arm are hidden in audit/audit_key.json (do not open it until
the audit is finished).
    python tools/make_audit.py  ->  audit/audit_blind.html, audit/audit_key.json
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import design  # noqa: E402
import run  # noqa: E402
from verify import Labeller  # noqa: E402

SEED = 20261116
PER_CELL = 25
RELEVANCE_N = 50
CONDS = ("P10", "A10", "P<10", "A<10")


def build(rows, label_of, seed=SEED, per_cell=PER_CELL):
    rng = random.Random(seed)
    pool = {}
    for r in sorted(rows, key=lambda r: r["id"]):
        if r["condition"] not in CONDS:
            continue
        for t in r["titles"]:
            lab = label_of(t)
            if lab is None:
                continue
            group = "unmatched" if lab == "unresolved" else "matched"
            pool.setdefault((r["condition"], group), []).append({"title": t, "topic": r["topic"],
                                                                 "condition": r["condition"], "label": lab,
                                                                 "group": group, "request": r["id"]})
    picked, seen = [], set()
    for key in sorted(pool):
        cand = pool[key][:]
        rng.shuffle(cand)
        by_topic = {}
        for c in cand:                       # round-robin over topics to spread the sample
            by_topic.setdefault(c["topic"], []).append(c)
        order = []
        while any(by_topic.values()):
            for tp in sorted(by_topic):
                if by_topic[tp]:
                    order.append(by_topic[tp].pop(0))
        n = 0
        for c in order:
            k = c["title"].lower()
            if k in seen:
                continue
            seen.add(k)
            picked.append(c)
            n += 1
            if n == per_cell:
                break
    rng.shuffle(picked)
    for i, p in enumerate(picked, 1):
        p["id"] = i
        p["relevance"] = i <= RELEVANCE_N
    return picked


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Blind audit</title>
<style>
:root{--bg:#f7f5f0;--ink:#1c1b19;--mute:#6b675f;--line:#d9d4c8;--ok:#1f6f43;--bad:#b3261e;--card:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#171614;--ink:#ece8df;--mute:#9a958a;--line:#34312c;--ok:#6fcf97;--bad:#ff8a80;--card:#201f1c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,Segoe UI,sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px;z-index:2}
h1{font-size:18px;margin:0 0 4px}header p{margin:0;color:var(--mute);font-size:14px}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}main{max-width:860px;margin:0 auto;padding:16px}
.row{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin-bottom:10px}
.row.done{opacity:.72}.meta{color:var(--mute);font-size:13px}.title{font-weight:600;margin:2px 0 8px;overflow-wrap:anywhere}
button,a.btn{font:inherit;font-size:14px;padding:6px 12px;border-radius:6px;border:1px solid var(--line);background:transparent;color:var(--ink);cursor:pointer;text-decoration:none;display:inline-block}
button.on.ok{background:var(--ok);color:#fff;border-color:var(--ok)}button.on.bad{background:var(--bad);color:#fff;border-color:var(--bad)}
.acts{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:4px}.q{font-size:13px;color:var(--mute);min-width:150px}
input.note{font:inherit;font-size:14px;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:transparent;color:var(--ink);flex:1;min-width:160px}
</style></head><body>
<header><h1>Blind audit: is this a real paper?</h1>
<p>Search each title (Scholar, then Google). <b>Real</b> = a paper with this title exists (punctuation and capitals don't matter). <b>Not found</b> = you can't find it. Rows with a second question: is the paper on the topic shown? Marks save in this browser.</p>
<div class="bar"><span id="count"></span><button id="dl">Download filled CSV</button><label style="font-size:14px"><input type="checkbox" id="hide"> hide finished</label></div></header>
<main id="list"></main>
<script>
const DATA = __DATA__;
const KEY = "audit_epistemics_v1";
let S = {}; try { S = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} };
const list = document.getElementById("list"), hide = document.getElementById("hide");
function done(r) { const s = S[r.id] || {}; return !!s.v && (!r.relevance || !!s.rel); }
function choice(r, field, pairs) {
  const wrap = document.createElement("span"); const st = S[r.id] || {};
  for (const [v, label, cls] of pairs) {
    const b = document.createElement("button"); b.textContent = label; b.className = cls + (st[field] === v ? " on" : "");
    b.onclick = () => { const cur = S[r.id] || {}; cur[field] = cur[field] === v ? "" : v; S[r.id] = cur; save(); render(); };
    wrap.appendChild(b); wrap.append(" ");
  }
  return wrap;
}
function render() {
  list.textContent = ""; let n = 0;
  for (const r of DATA) {
    if (done(r)) n++;
    if (hide.checked && done(r)) continue;
    const d = document.createElement("div"); d.className = "row" + (done(r) ? " done" : "");
    const m = document.createElement("div"); m.className = "meta"; m.textContent = "#" + r.id + " · topic: " + r.topic;
    const t = document.createElement("div"); t.className = "title"; t.textContent = r.title;
    const a = document.createElement("div"); a.className = "acts";
    const q = encodeURIComponent('"' + r.title + '"');
    for (const [label, url] of [["Scholar", "https://scholar.google.com/scholar?q=" + q], ["Google", "https://www.google.com/search?q=" + q]]) {
      const l = document.createElement("a"); l.className = "btn"; l.textContent = label; l.href = url; l.target = "_blank"; l.rel = "noopener"; a.appendChild(l);
    }
    a.appendChild(choice(r, "v", [["real", "Real", "ok"], ["fabricated", "Not found", "bad"]]));
    d.append(m, t, a);
    if (r.relevance) {
      const b = document.createElement("div"); b.className = "acts";
      const lab = document.createElement("span"); lab.className = "q"; lab.textContent = "On the topic above?";
      b.append(lab, choice(r, "rel", [["on", "On topic", "ok"], ["off", "Off topic", "bad"]]));
      d.appendChild(b);
    }
    const n2 = document.createElement("div"); n2.className = "acts";
    const note = document.createElement("input"); note.className = "note"; note.placeholder = "note (optional)"; note.value = (S[r.id] || {}).n || "";
    note.oninput = () => { const cur = S[r.id] || {}; cur.n = note.value; S[r.id] = cur; save(); };
    n2.appendChild(note); d.appendChild(n2); list.appendChild(d);
  }
  document.getElementById("count").textContent = n + " of " + DATA.length + " done";
}
hide.onchange = render;
const esc = s => '"' + String(s || "").replace(/"/g, '""') + '"';
document.getElementById("dl").onclick = () => {
  const lines = ["id,topic,title,verdict,relevance,note"];
  for (const r of DATA) { const s = S[r.id] || {}; lines.push([r.id, esc(r.topic), esc(r.title), s.v || "", s.rel || "", esc(s.n)].join(",")); }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv" }));
  a.download = "audit_filled.csv"; a.click();
};
render();
</script></body></html>"""


def main():
    cfg = design.load_config()
    lab = Labeller(cfg)
    picked = build(run.arm_rows("gptoss"), lambda t: lab.label(t, lookup=False)[0])
    out = ROOT / "audit"
    out.mkdir(exist_ok=True)
    public = [{"id": p["id"], "topic": p["topic"], "title": p["title"], "relevance": p["relevance"]} for p in picked]
    data = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
    (out / "audit_blind.html").write_text(PAGE.replace("__DATA__", data), "utf-8")
    (out / "audit_key.json").write_text(json.dumps({str(p["id"]): {k: p[k] for k in ("condition", "label", "group", "request")}
                                                    for p in picked}, ensure_ascii=False, indent=1), "utf-8")
    from collections import Counter
    print(len(picked), "titles;", dict(Counter((p["condition"], p["group"]) for p in picked)))


if __name__ == "__main__":
    main()
