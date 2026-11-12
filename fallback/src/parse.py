"""Parse a judge's reply into (exists, confidence). Anything unclear is flagged for blind manual scoring."""
import re

_EXISTS = re.compile(r"^\W*EXISTS\W*:\W*(yes|no|uncertain)\b", re.I | re.M)
_CONF = re.compile(r"^\W*CONFIDENCE\W*:\W*(\d{1,3})\b", re.I | re.M)


def parse(text):
    ex = _EXISTS.findall(text or "")
    cf = _CONF.findall(text or "")
    exists = ex[-1].lower() if ex else None
    conf = int(cf[-1]) if cf else None
    if conf is not None and not 0 <= conf <= 100:
        conf = None
    # Two different EXISTS answers in one reply is a contradiction: do not guess which one was meant.
    contradictory = len({e.lower() for e in ex}) > 1
    return {"exists": None if contradictory else exists, "confidence": conf,
            "ok": exists is not None and conf is not None and not contradictory,
            "contradictory": contradictory}


def p_exists(parsed):
    """Stated probability that the paper exists, from the EXISTS answer and its confidence."""
    if not parsed.get("ok"):
        return None
    c = parsed["confidence"] / 100
    return {"yes": c, "no": 1 - c, "uncertain": 0.5}[parsed["exists"]]
