"""Deterministic gates. Nothing here asks a model whether the output is good -
these are the failures that are cheap to detect and expensive to publish."""
from __future__ import annotations

import re

import voice

MIN_WORDS, MAX_WORDS = 120, 300

# --- spelling -----------------------------------------------------------------
# Eleven of the twenty-four writers are American and thirteen are not, and the models
# spell American by default. Orwell writing "labor" and Kafka "mechanized" is a
# pastiche error of the same kind as a date or a modern word; Twain writing "labor"
# is correct and must never be touched. So this is keyed on the WRITER, not applied
# to the site - which is why it lives beside the anachronism tells rather than in a
# tidy-up script.
#
# Measured over the 66 published essays: seven instances across five writers, all of
# them in the non-American half - orwell, russell and tolstoy on "labor", montaigne
# and russell on "neighbor", kafka on "mechanized", nietzsche on "anesthesia".
AMERICAN = {"bourdain", "child", "dickinson", "didion", "ephron", "franklin",
            "thompson", "thoreau", "twain", "wallace", "whitman"}

# Deliberately conservative. Every entry here is wrong in Australian English in every
# context. The near misses that are NOT in the list, and why:
#   practice  a noun, and correct as one; only the verb is "practise"
#   program   Australian usage keeps "program"
#   gray      a valid variant, and a surname
#   meter     correct for the device, wrong only for the unit
#   story     a floor is a storey, a tale is a story
US_SPELLING = {
    "theater": "theatre", "color": "colour", "colors": "colours",
    "colored": "coloured", "honor": "honour", "honored": "honoured",
    "labor": "labour", "labors": "labours", "neighbor": "neighbour",
    "neighbors": "neighbours", "favorite": "favourite", "flavor": "flavour",
    "odor": "odour", "rumor": "rumour", "splendor": "splendour",
    "vapor": "vapour", "behavior": "behaviour", "defense": "defence",
    "offense": "offence", "pretense": "pretence", "center": "centre",
    "centers": "centres", "fiber": "fibre", "somber": "sombre",
    "traveled": "travelled", "traveling": "travelling", "canceled": "cancelled",
    "marveled": "marvelled", "anesthesia": "anaesthesia",
    "anesthetic": "anaesthetic", "esthetic": "aesthetic", "maneuver": "manoeuvre",
    "plow": "plough", "catalog": "catalogue", "dialog": "dialogue",
    "analog": "analogue", "mold": "mould", "smolder": "smoulder",
    "realize": "realise", "realized": "realised", "organize": "organise",
    "organized": "organised", "recognize": "recognise",
    "recognized": "recognised", "apologize": "apologise", "analyze": "analyse",
    "mechanized": "mechanised", "civilization": "civilisation",
    "civilized": "civilised", "sterilized": "sterilised",
    "memorialize": "memorialise", "criticize": "criticise",
    "sympathize": "sympathise", "emphasize": "emphasise",
}
_US = re.compile(r"\b(" + "|".join(sorted(US_SPELLING)) + r")\b", re.I)


def us_spellings(text: str) -> list[tuple[str, str]]:
    """Every American spelling in `text`, as (found, Australian form)."""
    seen, out = set(), []
    for m in _US.finditer(text or ""):
        w = m.group(1).lower()
        if w not in seen:
            seen.add(w)
            out.append((m.group(1), US_SPELLING[w]))
    return out

# Phrases that give away the pastiche as pastiche, or that are the model talking
# about the task instead of doing it.
TELLS = [
    "as a writer", "in my time", "in my day", "centuries ago", "in my century",
    "had i lived", "were i alive", "in this modern age", "modern reader",
    "little did", "i could not have imagined", "in my own era",
]


def check(essay: str, thinker: dict, shots: dict[str, str],
          verdict: str = "-", score: float | None = None,
          on_topic: bool = True) -> list[str]:
    """Every reason this essay should not be published. Empty list means fine."""
    problems = []
    # Judged by the scoring pass, which has already read the prose. A keyword test
    # cannot do this job: the essay is told not to define or explain its object, so
    # the literal word is often and legitimately absent.
    if not on_topic:
        problems.append("never engages the object")
    # The score is shown beside the essay, so a missing or absurd one is a broken
    # page rather than a cosmetic flaw. Whether the PROSE matches the number is not
    # checkable here - that lives in the prompt and in reading the output.
    if score is None or not 0 <= score <= 10:
        problems.append(f"score {score!r}, want 0-10")
    if not 1 <= len(verdict.split()) <= 3:
        problems.append(f"verdict {verdict!r}, want one to three words")
    # The verdict is the SITE speaking, not the writer: it prints in a column beside
    # sixty-five others, under a heading in the site's own voice. So it is Australian
    # English whoever the essay is by - a column carrying both "theater" and "theatre"
    # reads as a mistake rather than as characterisation. Five of the sixty-six were
    # American: catalog, organized, anesthesia, mechanized, theater.
    for found, au in us_spellings(verdict):
        problems.append(f"verdict spells {found!r}, want {au!r}")
    if re.search(r"\d(?:\.\d)?\s*(?:/|out of)\s*(?:10|ten)|\bten out of ten\b",
                 essay, re.I):
        problems.append("states a score in the essay")
    if "_" in essay or "*" in essay:
        problems.append("markdown emphasis in the prose")
    # No English word triples a letter, so this only ever fires on a slip. Kafka's
    # first alarm-clock essay published with "rearrrange" in it; cheap to detect and
    # embarrassing to leave up, which is what this file is for.
    for w in re.findall(r"[A-Za-z']+", essay):
        if re.search(r"(.)\1\1", w, re.I):
            problems.append(f"letter tripled in {w!r}")
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
    # American spelling in a writer who was not American. See AMERICAN above: this is
    # a fault in Orwell and correct in Twain, so it is keyed on the writer.
    # A missing id is reported rather than shrugged off. Defaulting either way is a
    # silent failure: assume American and the gate is off for a writer who needs it,
    # assume not and it fires on one who does not. Neither shows up in a green run.
    if "id" not in thinker:
        problems.append("thinker has no id, so the spelling gate cannot run")
    elif thinker["id"] not in AMERICAN:
        for found, au in us_spellings(essay):
            problems.append(f"American spelling {found!r} in a writer who was not, "
                            f"want {au!r}")
    if essay.count('"') > 6:
        problems.append("reads as dialogue, not an essay")

    # THE FILLER GATES. Added 29/08/2026 after reading all fifty-eight published
    # essays and measuring them. The corpus split hard by the model that WROTE it:
    # Gemini's 28 averaged 3.3 concrete anchors and 0.21 hedges, llama-3.3-70b's 30
    # averaged 0.3 and 0.83. The second group is not worse pastiche, it is a different
    # genre - costume drama with no stance, hedged into saying nothing. Franklin on
    # LinkedIn managed "the notion of it is intriguing, though its practical
    # applications are not entirely clear to me" and stopped there.
    #
    # A CONCRETENESS gate was the obvious fix and was tried and REJECTED: requiring
    # one concrete anchor would have failed 17 of the 28 good essays, because
    # Montaigne, Aurelius and Kafka are legitimately abstract. Being specific
    # separates Didion from filler; it does not separate Montaigne from filler.
    # The three below were each measured against the published corpus first, and
    # between them they catch 12 of 58 with ZERO of Gemini's essays among them.
    #
    # "I must confess" and "is it not" were in the first draft of this list and taken
    # out: both read correctly in Montaigne and Franklin, and a gate that costs a
    # legitimate line is not worth its catch.
    for m in re.findall(r"\b(a testament to|relentless pursuit|the very act of)\b",
                        essay, re.I):
        problems.append(f"stock phrase: {m.lower()!r}")
    # Hedging is fine once. Three times in 200 words is a writer with no opinion,
    # which is the one thing none of these writers are.
    hedges = re.findall(r"\b(perhaps|somewhat|rather|seems? to|appears? to|one might"
                        r"|may well|not entirely|I must say|intriguing|the notion of)\b",
                        essay, re.I)
    if len(hedges) >= 3:
        problems.append(f"hedged {len(hedges)} times, so it takes no position")
    # "a metallic flower, a perforated disk, a sprinkle of tiny holes". Whitman on the
    # hot shower was nine of these end to end, no verb doing any work, and it scored
    # 8.5 - the highest on the site - because a catalogue has nothing in it to dislike.
    if len(re.findall(r"\ba [\w\s]{2,20}, a [\w\s]{2,20}, a [\w\s]{2,20}\b",
                      essay, re.I)) >= 2:
        problems.append("runs of three appositives: a catalogue, not an essay")

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
