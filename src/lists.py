"""Reading a numbered title list out of a reply. Same rule as the MSc study's chat-mode extension
(pre-existing): numbered lines, title extracted, seed titles and repeats dropped, first ten kept."""
import re

from titles import extract

SEED_TITLES = ("Attention Is All You Need", "Deep Residual Learning for Image Recognition",
               "Adam: A Method for Stochastic Optimization")
ITEM = re.compile(r"^\s*(\d+)\s*[.)]\s*(\S.*)$")
_SEED_KEYS = {re.sub(r"[^a-z0-9]", "", t.lower()) for t in SEED_TITLES}
N_TITLES = 10


def key(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())


def numbered_items(text):
    """[(item_number, title)] for every numbered line, in order, before any filtering."""
    out = []
    for line in (text or "").splitlines():
        m = ITEM.match(line)
        if m:
            out.append((int(m.group(1)), extract(m.group(2).strip())))
    return out


def scored_titles(text):
    """The titles that are scored: seed titles and repeats dropped, first ten kept.
    Returns (titles, n_dropped_repeats)."""
    seen, out, repeats = set(_SEED_KEYS), [], 0
    for _, t in numbered_items(text):
        k = key(t)
        if not t:
            continue
        if k in seen:
            if k not in _SEED_KEYS:
                repeats += 1
            continue
        seen.add(k)
        out.append(t)
    return out[:N_TITLES], repeats
