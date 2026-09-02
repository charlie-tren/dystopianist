"""The scores on the front page have to be one measurement, not several.

A score is meaningless on its own: it exists to be compared with the other scores in
the same column, and the front page sorts on it. So the failure this guards is not a
wrong number, which no test can see, but a corpus scored by more than one model - two
scales printed as one, which looks exactly like a working page.

It happened. On 26/08/2026 Gemini's free tier was spent by the time the batch ran, so
llama-3.3-70b scored 22 essays while Gemini had scored the 17 before them, and nothing
anywhere recorded that. See tools/rescore.py for the measurement.

The archive is drained onto one scale a few essays a night, so an off-scale BACKLOG is
the expected state for now and does not fail. What fails is the regression: a newly
written essay that does not record who scored it, which is how the last mix went
unnoticed for two days.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import write as write_stage        # noqa: E402


def main() -> int:
    entries = json.loads((ROOT / "data" / "essays.json").read_text(encoding="utf-8"))
    if not entries:
        print("no essays yet")
        return 0

    problems = []
    by = collections.Counter(e.get("scored_by") or "(not recorded)" for e in entries)
    canon = f"{write_stage.SCORER}/{write_stage.SCALE}"
    off = sum(1 for e in entries if e.get("scored_by") != canon)
    unscored = [e for e in entries if e.get("score") is None]

    print(f"{len(entries)} essays; scored by {dict(by)}")
    print(f"  canonical scale is {canon!r}; {off} still off it")

    # The regression check: the newest essay must record who scored it.
    #
    # This WAS expressed as a ratchet - "once the archive starts recording, it never
    # stops" - and that was wrong, in a way a green run hid for two days. rescore.py
    # repairs the OLDEST entries first, so index 0 gains the field while the fifty
    # behind it have not been reached yet. The ratchet read that legitimate shape as
    # a regression and failed with 37 false positives the first time the drain
    # actually ran.
    #
    # Position is the wrong signal. A repair never appends; a new essay always does.
    # So the question is only ever about the last entry, and it can still fail for
    # the reason the check exists: if run.py stops recording the field, tomorrow's
    # essay lands without it and this goes red the next morning.
    newest = entries[-1]
    if not newest.get("scored_by"):
        problems.append(
            f"the newest essay ({newest['thinker']}/{newest['object']}, "
            f"{newest['date']}) records no scored_by - see write.score_essay and run.one")

    # A published essay with no number at all is a broken page, not a scale problem.
    if unscored:
        problems.append(f"{len(unscored)} essay(s) carry no score at all: "
                        + ", ".join(f"{e['thinker']}/{e['object']}" for e in unscored[:3]))

    # A value shared by a quarter of the archive is the symptom that started this.
    # Not a failure - a real corpus can genuinely bunch - but it should be visible
    # rather than something someone notices by reading the page.
    counts = collections.Counter(e["score"] for e in entries if e.get("score") is not None)
    worst, n = counts.most_common(1)[0] if counts else (None, 0)
    print(f"  {len(counts)} distinct scores; most repeated is {worst} on {n} essays")

    if problems:
        for p in problems:
            print(f"FAIL: {p}", file=sys.stderr)
        return 1
    print("\nscores are recorded and accounted for")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
