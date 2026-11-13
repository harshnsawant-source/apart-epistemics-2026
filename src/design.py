"""The experimental design: conditions, the run manifest, and prompt text. Deterministic.

Conditions (every one includes the accuracy line):
  P10  archival notice + "return 10"        A10  audit notice + "return 10"
  P<10 archival notice + "fewer if unsure"  A<10 audit notice + "fewer if unsure"
  BASE the MSc study's prompt with nothing added (fresh A/A repeatability runs)
Order: topic x notice-pair blocks are shuffled; inside a block the four conditions are shuffled. So any day's
collection holds complete blocks, never one condition per day. Both notice wordings are main items.
Priority (FREEZE section 5): all main blocks first; the A/A repeats come last, so a quota shortfall drops them
first. Stage two runs between the two (see run.plan_order).
"""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONDITIONS = {"P10": ("archive", "ten"), "A10": ("audit", "ten"),
              "P<10": ("archive", "fewer"), "A<10": ("audit", "fewer")}


def load_json(rel):
    return json.loads((ROOT / rel).read_text("utf-8"))


def load_config():
    return load_json("config.json")


def call_seed(base_seed, *parts):
    """A stable, distinct seed per call (independent sampling across conditions)."""
    h = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return base_seed + int(h[:6], 16)


def manifest(cfg, topics):
    rng = random.Random(cfg["order_seed"])
    out = []
    # Arms added after the freeze go last, so the frozen arms keep their exact call order.
    order = cfg.get("arm_order") or sorted(cfg["arms"])
    for arm in order:
        spec = cfg["arms"][arm]
        main = [(t["topic"], p) for t in topics for p in spec["pairs"]]
        repeats = [(t["topic"], f"AA{k}") for t in topics for k in range(1, spec["aa_runs"] + 1)]
        rng.shuffle(main)
        rng.shuffle(repeats)
        blocks = main + repeats
        for topic, pair in blocks:
            if pair.startswith("AA"):
                conds = ["BASE"]
            else:
                conds = list(CONDITIONS)
                rng.shuffle(conds)
            for c in conds:
                out.append({"id": f"{arm}|{topic}|{pair}|{c}", "arm": arm, "topic": topic, "pair": pair,
                            "condition": c, "seed": call_seed(cfg["base_seed"], arm, topic, pair, c)})
    return out


def user_prompt(prompts, topic, pair, condition):
    base = prompts["base"].format(topic=topic)
    if condition == "BASE":
        return base
    notice, qty = CONDITIONS[condition]
    extra = " ".join([prompts["accuracy"], prompts["notices"][pair][notice], prompts["quantity"][qty]])
    return base + "\n\n" + extra


def guard(cfg):
    if "DRAFT" in Path(cfg["prompts"]).name.upper():
        raise SystemExit("Refusing to run: prompts are still a DRAFT. Freeze them first.")
    if not (ROOT / "FREEZE.md").exists():
        raise SystemExit("Refusing to run: FREEZE.md does not exist. Write and commit the plan first.")
