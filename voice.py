"""Measurable fingerprints of a piece of prose, and the distance between two.

This exists because the one real risk in this project is every thinker collapsing
into the same voice, and "it reads fine to me" is not a test. Wallace should have
long self-qualifying sentences; Diogenes short ones; Bierce almost no first person;
Veblen a Latinate vocabulary nobody else reaches for. Those are all countable.

None of this judges QUALITY. It only answers "are these two the same voice", which
is the failure mode a longer prompt would hide rather than fix.
"""
from __future__ import annotations

import math
import re

# Latinate/abstract endings, the Veblen-Debord axis
LATINATE = re.compile(r"\w+(?:tion|sion|ity|ism|ance|ence|ment|ious|eous|ary|ual)\b", re.I)
FIRST_PERSON = re.compile(r"\b(I|me|my|mine|myself)\b")
SECOND_PERSON = re.compile(r"\b(you|your|yours|yourself)\b")


# A full stop is not a sentence boundary after a title, an abbreviation or an initial.
# Splitting on one anyway is what put "One must admire the fortitude of Mrs." at the end
# of a paragraph and started the next with "Brown, who discovers...", found on the live
# site 29/08/2026. The list is deliberately short: only forms these writers actually
# use. Single capital letters cover initials - "H. G. Wells", "T. S. Eliot", "K." - and
# are the most common case here by some way.
ABBREV = (r"Mr|Mrs|Ms|Dr|St|Prof|Rev|Sr|Jr|Hon|Capt|Gen|Col|Sgt|Lt|Ave|No|vs|etc"
          r"|e\.g|i\.e|cf|approx|Fig|Vol|pp|al|Co|Ltd|Inc")
_SPLIT = re.compile(r"(?<=[.!?])\s+(?!\s)")
_NO_BREAK = re.compile(rf"(?:\b(?:{ABBREV})|(?:^|[\s(\"'])[A-Z])\.$")


def sentences(text: str) -> list[str]:
    """Split on sentence boundaries, keeping abbreviations and initials intact.

    Used for BOTH the rendered paragraphs and the voice fingerprint, because a
    mis-split is two bugs: a paragraph that begins mid-sentence, and a sentence-length
    average pulled down by fragments that were never sentences."""
    out = []
    for part in _SPLIT.split(text.strip()):
        if out and _NO_BREAK.search(out[-1]):
            out[-1] += " " + part
        else:
            out.append(part)
    return [p for p in out if p.strip()]


def fingerprint(text: str) -> dict:
    words = re.findall(r"[A-Za-z']+", text)
    sents = sentences(text)
    if not words or not sents:
        return {k: 0.0 for k in
                ("mean_sent", "sent_spread", "long_words", "latinate", "first", "second", "commas", "ttr")}
    lens = [len(re.findall(r"[A-Za-z']+", s)) for s in sents]
    mean = sum(lens) / len(lens)
    var = sum((x - mean) ** 2 for x in lens) / len(lens)
    n = len(words)
    return {
        "mean_sent": mean,                                   # sentence length
        "sent_spread": math.sqrt(var),                       # ... and how varied
        "long_words": sum(len(w) > 7 for w in words) / n,
        "latinate": len(LATINATE.findall(text)) / n,
        "first": len(FIRST_PERSON.findall(text)) / n,
        "second": len(SECOND_PERSON.findall(text)) / n,
        "commas": text.count(",") / len(sents),
        "ttr": len({w.lower() for w in words}) / n,          # lexical variety
    }


# Scales that turn each raw feature into roughly comparable units, so no single
# one dominates the distance. Derived from the spread seen across the eight
# reference shots rather than picked by eye.
# NOTE the absence of ttr. Type-token ratio is LENGTH-DEPENDENT: a 45-word sample
# scores ~0.8 and a 190-word essay ~0.70 whatever the voice, so including it made
# every essay look most like whichever reference shot had the lowest ttr - which
# happened to be Veblen, and three thinkers in a row failed the gate as "reads
# more like veblen". Measured, not guessed. Everything left is either a ratio or a
# per-sentence average, so it survives comparing a short shot with a long essay.
SCALE = {"mean_sent": 12.0, "sent_spread": 8.0, "long_words": 0.08, "latinate": 0.05,
         "first": 0.04, "second": 0.05, "commas": 1.5}


def distance(a: dict, b: dict) -> float:
    """Euclidean distance between two fingerprints in scaled units."""
    return math.sqrt(sum(((a[k] - b[k]) / SCALE[k]) ** 2 for k in SCALE))


def divergence(texts: dict[str, str]) -> tuple[float, tuple[str, str]]:
    """Smallest distance between any two of these voices, and which pair it was.
    The MINIMUM is the number that matters: one pair collapsing is the failure,
    and an average would hide it behind six healthy pairs."""
    fps = {k: fingerprint(v) for k, v in texts.items()}
    worst, pair = float("inf"), ("", "")
    keys = sorted(fps)
    for i, x in enumerate(keys):
        for y in keys[i + 1:]:
            d = distance(fps[x], fps[y])
            if d < worst:
                worst, pair = d, (x, y)
    return worst, pair
