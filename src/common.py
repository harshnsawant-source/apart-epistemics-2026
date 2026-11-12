"""Shared helpers. Standard library only."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(s):
    # Same normaliser as the MSc study's verify.py (pre-existing): lowercase, keep a-z 0-9, collapse spaces.
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())


def load_config(path=None):
    p = Path(path) if path else ROOT / "config.json"
    return json.loads(p.read_text("utf-8"))


def resolve(p):
    p = Path(p)
    return p if p.is_absolute() else (ROOT / p).resolve()


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text("utf-8").splitlines() if l.strip()]


def append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
