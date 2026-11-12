"""Collect judge responses. Resumable: rows already in raw/responses.jsonl are skipped.

Per (judge, title): one INITIAL reply in a fresh context, then two continuations that both fork from that
same saved initial reply: NEUTRAL (asked to assess again) and CHALLENGE ("I could not find this paper").

Safety: refuses to call a real model unless FREEZE.md exists and the prompts file is not a DRAFT.
Run: python src/collect.py [--judge NAME] [--limit N]
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, append_jsonl, load_config, read_jsonl, resolve
from parse import parse

OUT = ROOT / "raw" / "responses.jsonl"


class DailyLimit(Exception):
    pass


def _groq_key():
    key = os.environ.get("GROQ_API_KEY")
    if not key and os.name == "nt":            # set with setx after this shell started
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key = winreg.QueryValueEx(k, "GROQ_API_KEY")[0]
        except OSError:
            key = None
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    return key


def call_groq(model, messages, cfg):
    body = json.dumps({"model": model, "messages": messages, "temperature": cfg["temperature"],
                       "seed": cfg["gen_seed"], "max_completion_tokens": cfg["max_tokens"]}).encode()
    for attempt in range(8):
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {_groq_key()}",
                     "User-Agent": "citation-recheck/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            m = d["choices"][0]["message"]
            return {"text": m.get("content") or "", "reasoning_chars": len(m.get("reasoning") or ""),
                    "usage": d.get("usage") or {}, "model_used": d.get("model"),
                    "finish": d["choices"][0].get("finish_reason")}
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = float(e.headers.get("retry-after") or 30)
            if wait > 900:                       # daily quota: stop cleanly, the run is resumable
                raise DailyLimit(f"Groq asks to wait {wait:.0f}s")
            time.sleep(wait + 1)
    raise RuntimeError("Groq: too many 429s")


def call_ollama(model, messages, cfg):
    body = json.dumps({"model": model, "messages": messages, "stream": False,
                       "options": {"temperature": cfg["temperature"], "seed": cfg["gen_seed"],
                                   "num_predict": cfg["max_tokens"]}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    return {"text": d["message"]["content"], "reasoning_chars": 0,
            "usage": {"prompt_tokens": d.get("prompt_eval_count"), "completion_tokens": d.get("eval_count")},
            "model_used": d.get("model"), "finish": d.get("done_reason")}


BACKENDS = {"groq": call_groq, "ollama": call_ollama}


def build_messages(prompts, title, branch, initial_text=None):
    msgs = [{"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompts["initial"].format(title=title)}]
    if branch != "initial":
        msgs += [{"role": "assistant", "content": initial_text},
                 {"role": "user", "content": prompts[branch]}]
    return msgs


def run(items, judges, prompts, cfg, out=OUT, call=None, limit=None):
    """call(backend, model, messages, cfg) -> dict; injected in tests."""
    call = call or (lambda b, m, msgs, c: BACKENDS[b](m, msgs, c))
    done = {(r["judge"], r["item_id"], r["branch"]): r for r in read_jsonl(out)}
    order = list(items)
    random.Random(cfg["order_seed"]).shuffle(order)
    made = 0
    for judge, spec in judges.items():
        for it in order:
            for branch in ("initial", "neutral", "challenge"):
                key = (judge, it["id"], branch)
                if key in done:
                    continue
                if limit is not None and made >= limit:
                    return made
                init = done.get((judge, it["id"], "initial"))
                msgs = build_messages(prompts, it["title"], branch, init["text"] if init else None)
                res = call(spec["backend"], spec["model"], msgs, cfg)
                row = {"judge": judge, "item_id": it["id"], "branch": branch, "messages": msgs,
                       "text": res["text"], "parsed": parse(res["text"]),
                       "usage": res.get("usage"), "reasoning_chars": res.get("reasoning_chars"),
                       "model_used": res.get("model_used"), "finish": res.get("finish"),
                       "utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                append_jsonl(out, row)
                done[key] = row
                made += 1
    return made


def guard(cfg):
    if "DRAFT" in Path(cfg["prompts"]).name.upper():
        raise SystemExit("Refusing to run: prompts file is still a DRAFT. Freeze it first.")
    if not (ROOT / "FREEZE.md").exists():
        raise SystemExit("Refusing to run: FREEZE.md does not exist. Write and commit the plan first.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    cfg = load_config()
    guard(cfg)
    prompts = json.loads(resolve(cfg["prompts"]).read_text("utf-8"))
    items = json.loads((ROOT / "data" / "manifest.json").read_text("utf-8"))["items"]
    judges = {k: v for k, v in cfg["judges"].items() if not a.judge or k == a.judge}
    try:
        n = run(items, judges, prompts, cfg, limit=a.limit)
        print(n, "new responses")
    except DailyLimit as e:
        print("Stopped at the daily limit:", e, "- run again later; finished rows are kept.")


if __name__ == "__main__":
    main()
