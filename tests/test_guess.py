"""The guessing game, which can be wrong in ways that still render a playable page.

Four of the five checks here are about the ONE thing the game can silently stop being:
a test of the prose. A passage that names its own writer, an option list that never
offers half the roster, or a round drawn from one writer are all still a working page
with buttons on it, and all three make the answer available without reading a word.

The fifth is the payload itself. It is JSON inside a <script> block, so an essay
containing a `</script>` would close the block early and take the whole game down with
a syntax error - a failure that no amount of reading render.py finds, because it
depends on what a model wrote that night.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import render                      # noqa: E402
import styles                      # noqa: E402

ARCHIVE = json.loads((ROOT / "data" / "essays.json").read_text(encoding="utf-8"))
ROSTER = styles.load()


def payload() -> dict:
    return render.guess_data(ARCHIVE, ROSTER)


def a_passage_never_names_its_own_writer(fails):
    """The one leak that ends the game. Surnames and any forename over three letters,
    because "Marcus" is common enough to appear innocently and "Kafka" is not."""
    hits = 0
    for q in payload()["qs"]:
        name = payload()["writers"][q["w"]]["name"]
        for part in [p for p in re.split(r"[ ,.]+", name) if len(p) > 3]:
            if re.search(r"\b" + re.escape(part) + r"\b", q["t"], re.I):
                fails.append(f"the passage for {name} on {q['o']} names them")
            hits += 1
    print(f"  checked {hits} name forms against every passage")


def every_writer_is_answerable(fails):
    """A writer who can never be the answer is learnable as one to rule out, which is
    a way of scoring with nothing to do with reading. The roster and the answers have
    to be the same set, in both directions."""
    d = payload()
    on_offer = {w["id"] for w in d["writers"]}
    answers = {d["writers"][q["w"]]["id"] for q in d["qs"]}
    missing = sorted(on_offer - answers)
    if missing:
        fails.append("offered as options but never the answer: " + ", ".join(missing))
    stray = sorted(answers - on_offer)
    if stray:
        fails.append("an answer that is not in the options: " + ", ".join(stray))
    print(f"  {len(on_offer)} writers on offer, {len(answers)} of them answerable")


def a_passage_is_long_enough_to_have_a_voice_and_short_enough_to_be_a_clue(fails):
    """Under about fifty words there is no cadence to read; over the hard cap the
    passage is most of the essay, so there is nothing left to click through to and the
    long-sentence writers are marked out by block size rather than by their prose."""
    lens = sorted(len(q["t"].split()) for q in payload()["qs"])
    if not lens:
        fails.append("no passages at all"); return
    if lens[0] < 35:
        fails.append(f"shortest passage is {lens[0]} words, too short to have a voice")
    if lens[-1] > render.HARD:
        fails.append(f"longest passage is {lens[-1]} words, over the {render.HARD} cap")
    # And the clip has to leave whole words plus the ellipsis, never a severed one.
    for q in payload()["qs"]:
        if q["t"].endswith("…") and not q["t"][-2].isalnum():
            fails.append(f"clipped mid-punctuation: ...{q['t'][-30:]}")
    print(f"  passages run {lens[0]} to {lens[-1]} words, cap {render.HARD}")


def a_clipped_passage_keeps_the_long_sentence(fails):
    """The clip exists so Proust still reads as Proust. Reintroduce the fault it was
    written for - a passage that would run past the cap - and check it comes back
    unfinished rather than shortened to a different, tidier sentence."""
    long_one = "It was, " + ", ".join(["a clause that keeps going"] * 40) + ", and then it ended."
    got = render.clip(long_one)
    if not got.endswith("…"):
        fails.append("an over-long passage was not marked as unfinished")
    if len(got.split()) > render.HARD:
        fails.append(f"clip returned {len(got.split())} words, over the cap")
    if len(got.split()) < render.HARD * 0.6:
        fails.append(f"clip threw away too much: {len(got.split())} words")
    if render.clip("Short and finished.") != "Short and finished.":
        fails.append("clip touched a passage that was already inside the cap")
    print(f"  a {len(long_one.split())}-word sentence clips to "
          f"{len(got.split())} and stays unfinished")


def the_payload_survives_being_embedded(fails):
    """It ships as JSON inside a <script> block on a real page. Parse it back out of
    the rendered HTML rather than out of the function, because everything that can go
    wrong here happens between the two."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        real, render.DOCS = render.DOCS, Path(tmp)
        try:
            (render.DOCS / "faces").mkdir(parents=True)
            render.build(ARCHIVE, ROSTER)
            page = (render.DOCS / "guess.html").read_text(encoding="utf-8")
        finally:
            render.DOCS = real
    m = re.search(r'id="quiz-data">(.*?)</script>', page, re.S)
    if not m:
        fails.append("no quiz payload in the rendered page"); return
    d = json.loads(m.group(1))
    if "<" in m.group(1):
        fails.append("a raw < in the payload can close the script block early")
    if len(d["qs"]) != len(ARCHIVE):
        fails.append(f'{len(d["qs"])} passages for {len(ARCHIVE)} essays')
    for q in d["qs"]:
        if not (render.DOCS / "e" / f'{q["e"]}.html') or "/" in q["e"]:
            fails.append(f'bad essay link {q["e"]}')
    if 'href="guess.html"' not in page:
        fails.append("the page does not carry its own nav tab")
    print(f'  {len(d["qs"])} passages and {len(d["writers"])} writers survived the round trip')


def main() -> int:
    fails: list[str] = []
    for check in (a_passage_never_names_its_own_writer,
                  every_writer_is_answerable,
                  a_passage_is_long_enough_to_have_a_voice_and_short_enough_to_be_a_clue,
                  a_clipped_passage_keeps_the_long_sentence,
                  the_payload_survives_being_embedded):
        print(f"{check.__name__}:")
        check(fails)
    if fails:
        for f in fails:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("\nthe game is still a test of the prose")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
