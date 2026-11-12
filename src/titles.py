"""Pull the paper title out of a generated reference line.

Base (pretrained) models write references author-first ("Vapnik, V. N., 1990. The nature
of statistical learning theory, Springer"), so the title has to be separated from the
authors and the venue before it can be looked up: the Semantic Scholar match endpoint
returns nothing at all when author names are left in the query.
"""
from __future__ import annotations
import re

VENUE = re.compile(
    r",\s*(?:in\s+)?(?:IEEE|ACM|Springer|Elsevier|MIT Press|Morgan Kaufmann|Journal|J\.|Trans\.|"
    r"Transactions|Proc\.|Proceedings|Conference|Advances in|arXiv|vol\.?|Vol\.?|pp\.?|No\.|"
    r"[A-Z][a-z]+ (?:Press|University))\b.*$")
AUTHORS_THEN_YEAR = re.compile(r"^.{0,140}?\b(?:1[89]|20)\d{2}[a-z]?\b\s*[.,)]?\s*(.+)$")
LEADING_AUTHORS = re.compile(
    r"^(?:(?:[A-Z][A-Za-z''\-]+,\s*(?:[A-Z]\.\s*){1,4}|[A-Z]\.\s*[A-Z][A-Za-z''\-]+,?\s*)"
    r"(?:and\s+|&\s+|,\s*)?)+")


# A note the model appended in brackets at the very end.
TRAILING_NOTE = re.compile(r"\s*\([^()]*\)\s*$")
# Only the unambiguous ", by <author>" form. A bare " by First Last" rule was
# tried and cut real titles ("...Aggregation by Dilated Convolutions").
AUTHOR_TAIL = re.compile(r",\s*by\s+.+$")

QUOTED = re.compile(r"[“‘\"']([^”’\"']{15,200})[”’\"']")


def extract(line: str) -> str:
    """Best guess at the title inside one reference line; "" when nothing usable is left."""
    s = line.strip()
    s = re.sub(r"^\[?\d+[\].)]?\s*", "", s)          # leading item number
    q = QUOTED.search(s)
    if q:                                            # a quoted span IS the title
        return re.sub(r"\s+", " ", q.group(1)).strip().rstrip(" .,;:")
    m = AUTHORS_THEN_YEAR.match(s)
    # A year at the END of a title ("... Deep Learning 2018?") is not an
    # author-year prefix: only strip when a title-length remainder is left.
    if m and len(re.sub(r"[^A-Za-z]", "", m.group(1))) >= 8:
        s = m.group(1)                                # everything after the year
    else:
        s = LEADING_AUTHORS.sub("", s)                # no year: strip author-shaped prefix
    s = VENUE.sub("", s)                              # trailing venue / volume / pages
    s = re.split(r"\s+\(\d{4}\)|\s+[-–—]\s+", s)[0]
    s = s.strip().lstrip(" ,.;:‘“\"'").rstrip(" .,;:")
    s = TRAILING_NOTE.sub("", s)                      # "(again)", "(Revision 2)"
    s = AUTHOR_TAIL.sub("", s)                        # ", by Michael Nielsen"
    s = re.sub(r"\s+", " ", s).strip().rstrip(" .,;:")
    # Study rule (21 Oct 2026): at least two words and 8 characters. The pilot's
    # "a 4-letter word then a 3-letter word" rule rejected real titles such as
    # "Attention is not Explanation" and "On the Convergence of Adam".
    if len(s) < 8 or len(re.findall(r"[A-Za-z]\S*", s)) < 2:
        return ""
    return s
