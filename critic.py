"""Deterministic gates. Nothing here asks a model whether the output is good -
these are the failures that are cheap to detect and expensive to publish."""
from __future__ import annotations

import re

import voice

MIN_WORDS, MAX_WORDS = 120, 300

# Phrases that give away the pastiche as pastiche, or that are the model talking
# about the task instead of doing it.
TELLS = [
    "as a writer", "in my time", "in my day", "centuries ago", "in my century",
    "had i lived", "were i alive", "in this modern age", "modern reader",
    "little did", "i could not have imagined", "in my own era",
]


def check(essay: str, thinker: dict, shots: dict[str, str]) -> list[str]:
    """Every reason this essay should not be published. Empty list means fine."""
    problems = []
    words = re.findall(r"[A-Za-z']+", essay)
    if not (MIN_WORDS <= len(words) <= MAX_WORDS):
        problems.append(f"length {len(words)} words, want {MIN_WORDS}-{MAX_WORDS}")

    surname = thinker["name"].split()[-1].lower()
    if surname in essay.lower():
        problems.append(f"names the author ({surname})")
    if re.search(r"\b(1[6-9]\d{2}|20\d{2})\b", essay):
        problems.append("mentions a year")
    for t in TELLS:
        if t in essay.lower():
            problems.append(f"anachronism tell: {t!r}")
    if essay.count('"') > 6:
        problems.append("reads as dialogue, not an essay")

    # NO PER-ESSAY VOICE GATE HERE, on purpose. The first version rejected an essay
    # whose fingerprint sat nearer another thinker's sample than its own, and it was
    # WRONG: it killed a Bierce piece that opens "PNEUMATIC DRYER, n." and reads as
    # nobody but Bierce, because long Latinate third-person sentences are also
    # Veblen's markers. Three Debord attempts died the same way. The features cannot
    # separate two formal voices on one sample, and a gate that rejects good work
    # burns free-tier calls to do it.
    #
    # The voice machinery still earns its place, but as a CORPUS check that runs in
    # tests/test_voice.py: if every thinker collapses into one register the fleet
    # average shows it, which is the failure actually worth guarding.
    return problems
