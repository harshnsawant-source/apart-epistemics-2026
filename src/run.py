"""Collect, verify, and run stage two. Resumable: every finished call is on disk and is skipped next time.

    python src/run.py --arm gptoss --minutes 45      # what GitHub Actions runs every hour
    python src/run.py --arm llama --minutes 300      # on the laptop (local Ollama)
    python src/run.py --smoke 3                       # token/format check on NON-study topics, before freezing

Each run: (1) collect generation calls in manifest order until done, out of time, or Groq's daily quota is
used up; (2) label every scored title not yet labelled; (3) once all pair-1 P10 lists of the stage-two arm are
labelled, run stage two. Refuses to touch study topics until FREEZE.md exists and prompts are frozen.
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design  # noqa: E402
import lists  # noqa: E402
from llm import BACKENDS, DailyLimit, Transient  # noqa: E402
from verify import Labeller  # noqa: E402

ROOT = design.ROOT
SMOKE_TOPICS = ("protein structure prediction", "federated learning for healthcare", "speech emotion recognition")
BRANCHES = ("neutral", "audit", "receipts")
DECISION = re.compile(r"(?:item\s*)?(\d{1,2})\s*[.:)\-]?\s*\**\s*(KEEP|WITHDRAW)\b", re.I)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_jsonl(path):
    p = Path(path)
    return [json.loads(l) for l in p.read_text("utf-8").splitlines() if l.strip()] if p.exists() else []


def append_jsonl(path, row):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


SHARD = ""          # file suffix for this runner's share of the calls, e.g. ".s2" (set by --shard)


def gen_path(arm):
    """Where THIS runner writes an arm's replies."""
    return ROOT / "raw" / f"generations_{arm}{SHARD}.jsonl"


def stage2_path(arm):
    return ROOT / "raw" / f"stage2_{arm}{SHARD}.jsonl"


def _all_files(prefix):
    raw = ROOT / "raw"
    files = [raw / f"{prefix}.jsonl"] + sorted(raw.glob(f"{prefix}.s*.jsonl"))
    return [f for f in files if "_attempts" not in f.name]


def arm_rows(arm):
    """Every saved reply for an arm, from all runners' files."""
    return [r for f in _all_files(f"generations_{arm}") for r in read_jsonl(f)]


def stage2_rows(arm):
    return [r for f in _all_files(f"stage2_{arm}") for r in read_jsonl(f)]


def shard_filter(seq, shard):
    """Runner k of n takes items k-1, k-1+n, ... so the runners never overlap."""
    k, n = shard
    return [x for i, x in enumerate(seq) if i % n == k - 1]


def messages_for(prompts, topic, pair, condition):
    return [{"role": "system", "content": prompts["system"]},
            {"role": "user", "content": design.user_prompt(prompts, topic, pair, condition)}]


RETRIES = 3                  # FREEZE section 6: up to 3 retries for transport errors
BACKOFF = (10, 30, 60)       # seconds before retry 1, 2, 3 when the server gives no wait


def attempt(call, args, call_id, log, sleep=time.sleep):
    """Call with up to RETRIES retries on transport errors. Every attempt goes to `log`.
    Returns the reply, or None after the last retry fails. DailyLimit and other errors propagate (logged)."""
    for n in range(1, RETRIES + 2):
        try:
            res = call(*args)
        except Transient as e:
            append_jsonl(log, {"id": call_id, "attempt": n, "utc": now(), "outcome": str(e)})
            if n <= RETRIES:
                sleep(e.wait if e.wait is not None else BACKOFF[n - 1])
                continue
            append_jsonl(log, {"id": call_id, "attempt": n, "utc": now(), "outcome": "failed"})
            return None
        except DailyLimit as e:
            append_jsonl(log, {"id": call_id, "attempt": n, "utc": now(), "outcome": f"daily limit: {e}"})
            raise
        except Exception as e:
            append_jsonl(log, {"id": call_id, "attempt": n, "utc": now(), "outcome": f"error: {e!r}"[:300]})
            raise
        append_jsonl(log, {"id": call_id, "attempt": n, "utc": now(), "outcome": "ok"})
        return res


def collect(cfg, prompts, arm, items, call, out, deadline, limit=None, sleep=time.sleep, attempts_log=None,
            also_done=()):
    """call(backend, model, messages, temperature, seed, max_tokens) -> dict. Returns (made, stopped_reason).
    also_done: ids already collected by any runner (skipped)."""
    spec = cfg["arms"][arm]
    log = attempts_log or Path(out).with_name(Path(out).stem + "_attempts.jsonl")
    done = {r["id"] for r in read_jsonl(out)} | set(also_done)
    made, failed_in_row = 0, 0
    for it in items:
        if it["arm"] != arm or it["id"] in done:
            continue
        if time.time() > deadline:
            return made, "time"
        if limit is not None and made >= limit:
            return made, "limit"
        msgs = messages_for(prompts, it["topic"], it["pair"], it["condition"])
        try:
            res = attempt(call, (spec["backend"], spec["model"], msgs, cfg["temperature"], it["seed"],
                                 cfg["max_completion_tokens"]), it["id"], log, sleep)
        except DailyLimit as e:
            return made, f"daily limit: {e}"
        if res is None:
            failed_in_row += 1
            if failed_in_row >= 3:
                return made, "stopped: 3 failed calls in a row"
            continue
        failed_in_row = 0
        titles, repeats = lists.scored_titles(res["text"])
        append_jsonl(out, dict(it, messages=msgs, text=res["text"], titles=titles, repeats=repeats,
                               usage=res.get("usage"), reasoning_chars=res.get("reasoning_chars"),
                               model_used=res.get("model_used"), finish=res.get("finish"), utc=now()))
        done.add(it["id"])
        made += 1
    return made, "done"


def label_all(labeller, rows, deadline, max_failures_in_row=5):
    """Look up every scored title that has no label yet. Returns how many are still unlabelled.
    Stops looking up after several failures in a row (a blocked or down service); the rest wait for the next run."""
    left, fails = 0, 0
    for r in rows:
        for t in r["titles"]:
            if labeller.label(t, lookup=False)[0] is not None:
                continue
            if time.time() > deadline or fails >= max_failures_in_row:
                left += 1
                continue
            if labeller.label(t)[0] is None:
                left += 1
                fails += 1
            else:
                fails = 0
    return left


def label_parallel(labeller, rows, deadline, workers=4):
    """Deviation 3: label every unlabelled title, Crossref and OpenAlex looked up in parallel threads.
    Results are stored by the main thread only. Returns how many titles are still unlabelled."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from verify import second_look
    first = lambda r: not (r.get("arm") == "gptoss" and r.get("pair") == "1" and r.get("condition") == "P10")
    rows = sorted(rows, key=first)            # stable: stage-two lists first, the rest in collection order
    todo = list(dict.fromkeys(t for r in rows for t in r["titles"] if labeller.label(t, lookup=False)[0] is None))
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {}
        it = iter(todo)
        for t in it:
            if len(futures) >= workers * 2:
                break
            futures[ex.submit(second_look, t, labeller.sources)] = t
        while futures:
            for f in as_completed(list(futures)):
                t = futures.pop(f)
                if labeller.store_second_look(t, f.result(), save=False):
                    done += 1
                if done % 25 == 0:
                    labeller._save()
                if time.time() < deadline:
                    nxt = next(it, None)
                    if nxt is not None:
                        futures[ex.submit(second_look, nxt, labeller.sources)] = nxt
                break
    labeller._save()
    return sum(1 for t in todo if labeller.label(t, lookup=False)[0] is None)


def stage2_messages(prompts, row, branch, labeller):
    """None if any item 4-13 is not labelled yet."""
    s = prompts["stage2"]
    parts = []
    if branch in ("audit", "receipts"):
        parts.append(s["audit_notice"])
    if branch == "receipts":
        lines = [s["receipts_header"]]
        for n, t in lists.numbered_items(row["text"]):
            if not 4 <= n <= 13:
                continue
            lab = labeller.label(t, lookup=False)[0]
            if lab is None:
                return None
            lines.append((s["receipt_found"] if lab != "unresolved" else s["receipt_missing"]).format(n=n))
        parts.append("\n".join(lines))
    parts.append(s["instruction"])
    return row["messages"] + [{"role": "assistant", "content": row["text"]},
                              {"role": "user", "content": "\n\n".join(parts)}]


def parse_decisions(text):
    out = {}
    for n, d in DECISION.findall(text or ""):
        n = int(n)
        if 4 <= n <= 13 and n not in out:
            out[n] = d.upper()
    return out


def stage2(cfg, prompts, arm, labeller, call, deadline, shard=(1, 1)):
    spec = cfg["arms"][arm]
    out = stage2_path(arm)
    done = {r["id"] for r in stage2_rows(arm)}
    lists_ = sorted((r for r in arm_rows(arm) if r["pair"] == "1" and r["condition"] == "P10"), key=lambda r: r["id"])
    lists_ = shard_filter(lists_, shard)
    made = 0
    for r in lists_:
        for b in BRANCHES:
            sid = f"{r['id']}|{b}"
            if sid in done:
                continue
            if time.time() > deadline:
                return made, "time"
            msgs = stage2_messages(prompts, r, b, labeller)
            if msgs is None:
                continue
            try:
                res = attempt(call, (spec["backend"], spec["model"], msgs, cfg["temperature"],
                                     design.call_seed(cfg["base_seed"], sid), cfg["max_completion_tokens"]),
                              sid, out.with_name(out.stem + "_attempts.jsonl"))
            except DailyLimit as e:
                return made, f"daily limit: {e}"
            if res is None:
                continue
            append_jsonl(out, {"id": sid, "list_id": r["id"], "topic": r["topic"], "branch": b, "messages": msgs,
                               "text": res["text"], "decisions": parse_decisions(res["text"]),
                               "usage": res.get("usage"), "utc": now()})
            made += 1
    return made, "done"


def collection_open(cfg, when):
    """FREEZE section 6: collect only between the sprint kickoff and the cutoff (Sunday 18:00 IST).
    Labelling and analysis may continue after the cutoff; new model calls may not."""
    start = datetime.fromisoformat(cfg["collect_not_before_utc"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(cfg["collect_cutoff_utc"].replace("Z", "+00:00"))
    if when < start:
        return False, f"before the sprint kickoff ({cfg['collect_not_before_utc']})"
    if when >= end:
        return False, f"after the collection cutoff ({cfg['collect_cutoff_utc']}); remaining calls are reported as missing"
    return True, ""


def plan_order(cfg, arm, main_done, stage2_done):
    """FREEZE section 5: main conditions, then stage two, then A/A repeats (dropped first if quota runs short)."""
    spec = cfg["arms"][arm]
    if not main_done:
        return ["main"]
    if spec.get("stage2") and not stage2_done:
        return ["stage2"]
    if spec.get("aa_runs"):
        return ["aa"]
    return []


def make_call(spec):
    extra = spec.get("extra", {})

    def call(backend, model, msgs, temperature, seed, max_tokens):
        return BACKENDS[backend](model, msgs, temperature, seed, max_tokens, **extra)
    return call


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="gptoss")
    ap.add_argument("--minutes", type=float, default=45)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--label", action="store_true", help="only label titles (Crossref and OpenAlex, in parallel)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--shard", default="1/1", help="k/n: this runner does share k of n (separate output files)")
    ap.add_argument("--no-lookup", action="store_true",
                    help="use cached labels only (stage two still runs on titles already labelled)")
    ap.add_argument("--smoke", type=int, help="N calls per condition on non-study topics; writes raw/smoke_<arm>.jsonl")
    a = ap.parse_args()
    cfg = design.load_config()
    prompts = design.load_json(cfg["prompts"])
    deadline = time.time() + a.minutes * 60
    global SHARD
    shard = tuple(int(x) for x in a.shard.split("/"))
    SHARD = "" if shard == (1, 1) else f".s{shard[0]}"

    if a.smoke:
        items = [{"id": f"smoke|{a.arm}|{t}|{c}", "arm": a.arm, "topic": t, "pair": "1", "condition": c,
                  "seed": design.call_seed(cfg["base_seed"], "smoke", t, c)}
                 for t in SMOKE_TOPICS[:a.smoke] for c in list(design.CONDITIONS) + ["BASE"]]
        made, why = collect(cfg, prompts, a.arm, items, make_call(cfg['arms'][a.arm]), ROOT / "raw" / f"smoke_{a.arm}.jsonl", deadline)
        rows = read_jsonl(ROOT / "raw" / f"smoke_{a.arm}.jsonl")
        toks = [sum(v for k, v in (r["usage"] or {}).items() if k in ("prompt_tokens", "completion_tokens") and v) for r in rows]
        print(f"smoke: {made} new calls ({why}); {len(rows)} total; tokens per call: "
              f"mean {sum(toks) / max(1, len(toks)):.0f}, max {max(toks, default=0)}")
        for r in rows[-5:]:
            print(f"  {r['condition']:5s} {len(r['titles'])} titles, finish={r['finish']}")
        return

    design.guard(cfg)
    if a.label:
        lab = Labeller(cfg)
        rows = [r for arm in cfg["arms"] for r in arm_rows(arm)]
        print(f"labels: {label_parallel(lab, rows, deadline, workers=a.workers)} titles still unlabelled")
        return
    is_open, why_closed = collection_open(cfg, datetime.now(timezone.utc))
    topics = design.load_json(cfg["topics"])["topics"]
    items = [it for it in design.manifest(cfg, topics) if it["arm"] == a.arm]
    all_main = [it for it in items if it["condition"] != "BASE"]
    main_items = shard_filter(all_main, shard)
    aa_items = shard_filter([it for it in items if it["condition"] == "BASE"], shard)
    call = make_call(cfg["arms"][a.arm])
    labeller = None if a.no_verify else Labeller(cfg)
    n_lists = len(topics)                      # pair-1 P10 lists that get stage two (all runners)
    for _ in range(4):
        have = {r["id"] for r in arm_rows(a.arm)}
        main_done = all(it["id"] in have for it in all_main)
        if not main_done and all(it["id"] in have for it in main_items):
            print(f"{a.arm}: this runner's main calls are done; waiting for the other runner before stage two")
            break
        s2_have = len(stage2_rows(a.arm))
        phases = plan_order(cfg, a.arm, main_done, s2_have >= 3 * n_lists)
        if not phases:
            print(f"{a.arm}: all phases complete")
            break
        phase = phases[0]
        if not is_open:
            print(f"collection closed: {why_closed}")
            if labeller is not None and not a.no_lookup:
                rows = [r for arm in cfg["arms"] for r in arm_rows(arm)]
                print(f"labels: {label_all(labeller, rows, deadline)} titles still unlabelled")
            break
        if phase == "main":
            made, why = collect(cfg, prompts, a.arm, main_items, call, gen_path(a.arm), deadline, a.limit, also_done=have)
        elif phase == "stage2":
            if labeller is None:
                print("stage two needs labels; run without --no-verify")
                break
            made, why = stage2(cfg, prompts, a.arm, labeller, call, deadline, shard=shard)
        else:
            made, why = collect(cfg, prompts, a.arm, aa_items, call, gen_path(a.arm), deadline, a.limit, also_done=have)
        print(f"{a.arm} [{phase}] shard {a.shard}: {made} new calls ({why}); generations "
              f"{len(arm_rows(a.arm))}/{len(items)}, stage two {len(stage2_rows(a.arm))}")
        if labeller is not None and not a.no_lookup:
            rows = [r for arm in cfg["arms"] for r in arm_rows(arm)]
            print(f"labels: {label_all(labeller, rows, deadline)} titles still unlabelled")
        if why != "done" or made == 0:
            break


if __name__ == "__main__":
    main()
