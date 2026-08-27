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
    off = sum(1 for e in entries if e.get("scored_by") != write_stage.SCORER)
    unscored = [e for e in entries if e.get("score") is None]

    print(f"{len(entries)} essays; scored by {dict(by)}")
    print(f"  canonical scale is {write_stage.SCORER!r}; {off} still off it")

    # The regression check: once the archive starts recording who scored an essay it
    # must never stop. Expressed as a ratchet over the append-ordered archive rather
    # than as a count, so it needs no baseline constant to keep in step with the
    # backlog, and it stays silent about the legacy essays in front of the first
    # recorded one. A run that writes an essay without the field puts an unrecorded
    # entry after a recorded one, which is the only shape this can take.
    first = next((i for i, e in enumerate(entries) if e.get("scored_by")), None)
    if first is not None:
        missing = [e for e in entries[first:] if not e.get("scored_by")]
        if missing:
            problems.append(
                f"{len(missing)} essay(s) written after the archive started recording "
                "scored_by do not carry it, newest "
                f"{missing[-1]['thinker']}/{missing[-1]['object']} - see "
                "write.score_essay and run.one")

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
