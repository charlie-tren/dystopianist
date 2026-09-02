"""Australian English, and the one place it must NOT be enforced.

Eleven of the twenty-four writers are American. "Twain writing labor" is correct
pastiche and "Orwell writing labor" is a fault, so a spelling gate that does not know
which writer it is looking at is either useless or actively wrong - it would either
miss Orwell or rewrite Twain into someone else.

That makes the false-positive half of this file the important half. A gate that
corrects Mark Twain's spelling passes every test you would think to write about
spelling, and is worse than no gate at all.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import critic                      # noqa: E402
import styles                      # noqa: E402

ARCHIVE = json.loads((ROOT / "data" / "essays.json").read_text(encoding="utf-8"))
ROSTER = {t["id"]: t for t in styles.load()}


def the_american_list_is_real_and_current(fails):
    """A stale id here silently turns the gate off for a writer, or on for one who
    should be exempt, and nothing else would show it."""
    stray = sorted(critic.AMERICAN - set(ROSTER))
    if stray:
        fails.append("in critic.AMERICAN but not in the roster: " + ", ".join(stray))
    print(f"  {len(critic.AMERICAN)} American of {len(ROSTER)} on the roster, "
          "every id real")


def it_fires_on_a_writer_who_was_not_american(fails):
    orwell = ROSTER["orwell"]
    got = critic.check("The labor of it. " * 30, orwell, {}, verdict="a thing",
                       score=5.0)
    if not any("American spelling" in p for p in got):
        fails.append("'labor' in Orwell was not caught")
    print("  Orwell on 'labor': caught")


def it_leaves_an_american_writer_alone(fails):
    """The false positive that matters. Same word, same gate, must not fire."""
    twain = ROSTER["twain"]
    got = critic.check("The labor of it. " * 30, twain, {}, verdict="a thing",
                       score=5.0)
    if any("American spelling" in p for p in got):
        fails.append("'labor' in Twain was 'corrected', which is the wrong direction")
    # And every American spelling still standing in the live archive is in an
    # American writer, by construction. Report the count, not a bare pass.
    kept = sum(len(critic.us_spellings(e["essay"])) for e in ARCHIVE
               if e["thinker"] in critic.AMERICAN)
    print(f"  Twain on 'labor': left alone. {kept} American spellings stand in the "
          "archive's American writers")


def a_verdict_is_australian_whoever_wrote_it(fails):
    """The verdict is the site speaking, in a column beside sixty-five others."""
    for who in ("thompson", "orwell"):
        got = critic.check("A word. " * 40, ROSTER[who], {},
                           verdict="totalitarian theater", score=5.0)
        if not any("verdict spells" in p for p in got):
            fails.append(f"US spelling in a verdict was not caught for {who}")
    print("  'totalitarian theater' caught in both an American and a British writer")


def the_near_misses_do_not_fire(fails):
    """Each of these is correct Australian English and would be a real regression.
    They are the reason the word list is short."""
    safe = {
        "practice": "the practice of presenting oneself",   # noun, correct as-is
        "program": "a program of exercises",                # AU keeps program
        "gray": "a gray morning",                           # valid variant, and a name
        "meter": "the gas meter",                           # the device, not the unit
        "story": "a story about a horse",                   # a tale, not a floor
    }
    for word, phrase in safe.items():
        hit = critic.us_spellings(phrase)
        if hit:
            fails.append(f"{word!r} fired on {phrase!r} -> {hit}")
    print(f"  {len(safe)} correct-Australian near misses, none fired")


def the_live_archive_is_clean(fails):
    """Regression guard for tools/aufix.py. It ran once; this is what stops the next
    batch of essays quietly putting the spellings back."""
    bad = []
    for e in ARCHIVE:
        if e["thinker"] not in critic.AMERICAN:
            bad += [(e["thinker"], w) for w, _ in critic.us_spellings(e["essay"])]
        bad += [(e["thinker"], w) for w, _ in
                critic.us_spellings(e.get("verdict", ""))]
    if bad:
        fails.append(f"{len(bad)} American spellings live on the site: {bad[:6]}")
    print(f"  {len(ARCHIVE)} published essays and verdicts, {len(bad)} faults")


def main() -> int:
    fails: list[str] = []
    for check in (the_american_list_is_real_and_current,
                  it_fires_on_a_writer_who_was_not_american,
                  it_leaves_an_american_writer_alone,
                  a_verdict_is_australian_whoever_wrote_it,
                  the_near_misses_do_not_fire,
                  the_live_archive_is_clean):
        print(f"{check.__name__}:")
        check(fails)
    if fails:
        for f in fails:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("\nAustralian where it should be, American where it should be")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
