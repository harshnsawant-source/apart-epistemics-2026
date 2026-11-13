"""Print MORE, WAIT or STOP for a runner.
    python tools/status.py gptoss 1/2   -> gpt-oss share 1 of 2 (stops at the cutoff)
    python tools/status.py other        -> other models (stop at the cutoff) and title labelling (continues)
WAIT: this runner's main calls are done but the other runner's are not, so stage two cannot start yet.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import design  # noqa: E402
import run  # noqa: E402
from verify import Labeller  # noqa: E402

part = sys.argv[1] if len(sys.argv) > 1 else "gptoss"
cfg = design.load_config()
is_open, _ = run.collection_open(cfg, datetime.now(timezone.utc))
topics = design.load_json(cfg["topics"])["topics"]
items = design.manifest(cfg, topics)
if part == "gptoss":
    shard = tuple(int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "1/1").split("/"))
    arm = [it for it in items if it["arm"] == "gptoss"]
    have = {r["id"] for r in run.arm_rows("gptoss")}
    all_main = [it for it in arm if it["condition"] != "BASE"]
    mine_main = run.shard_filter(all_main, shard)
    mine_aa = run.shard_filter([it for it in arm if it["condition"] == "BASE"], shard)
    s2_done = {r["id"] for r in run.stage2_rows("gptoss")}
    lists_ = sorted((r for r in run.arm_rows("gptoss") if r["pair"] == "1" and r["condition"] == "P10"), key=lambda r: r["id"])
    n_lists_mine = len(run.shard_filter([t["topic"] for t in topics], shard))
    mine_s2_left = 3 * n_lists_mine - sum(1 for r in run.shard_filter(lists_, shard) for b in run.BRANCHES
                                          if f"{r['id']}|{b}" in s2_done)
    main_left = sum(1 for it in mine_main if it["id"] not in have)
    aa_left = sum(1 for it in mine_aa if it["id"] not in have)
    others_main_left = sum(1 for it in all_main if it["id"] not in have) - main_left
    print(f"gpt-oss share {shard[0]}/{shard[1]}: main left {main_left}, stage two left {mine_s2_left}, "
          f"repeats left {aa_left}, other share's main left {others_main_left}, collection open {is_open}")
    if not is_open:
        print("STOP")
    elif main_left:
        print("MORE")
    elif others_main_left:
        print("WAIT")
    else:
        print("MORE" if (mine_s2_left > 0 or aa_left) else "STOP")
else:
    gens_left = sum(1 for it in items if it["arm"] != "gptoss" and it["id"] not in
                    {r["id"] for a in cfg["arms"] for r in run.arm_rows(a)})
    lab = Labeller(cfg)
    rows = [r for a in cfg["arms"] for r in run.arm_rows(a)]
    unlabelled = len({t for r in rows for t in r["titles"] if lab.label(t, lookup=False)[0] is None})
    print(f"other generations left {gens_left}, unlabelled titles {unlabelled}, collection open {is_open}")
    print("MORE" if (is_open and gens_left) or unlabelled else "STOP")
