"""Print MORE if collection should continue, else STOP. Used by the cloud runner to start its next run."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import design  # noqa: E402
import run  # noqa: E402

cfg = design.load_config()
is_open, _ = run.collection_open(cfg, datetime.now(timezone.utc))
topics = design.load_json(cfg["topics"])["topics"]
items = design.manifest(cfg, topics)
have = {r["id"] for arm in cfg["arms"] for r in run.read_jsonl(run.gen_path(arm))}
gens_left = sum(1 for it in items if it["id"] not in have)
s2_left = sum(3 * len(topics) - len(run.read_jsonl(design.ROOT / "raw" / f"stage2_{a}.jsonl"))
              for a, s in cfg["arms"].items() if s.get("stage2"))
print(f"generations left {gens_left}, stage two left {s2_left}, collection open {is_open}")
print("MORE" if is_open and (gens_left or s2_left) else "STOP")
