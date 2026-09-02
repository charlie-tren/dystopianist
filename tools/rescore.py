"""Re-read published essays and put every score on ONE model's scale.

    python tools/rescore.py                # only the ones not on the canonical scale
    python tools/rescore.py --all          # every essay, whatever scored it
    python tools/rescore.py --limit 15     # stop after N, for a day-limited free tier
    python tools/rescore.py --dry          # show what would change, write nothing

WHY THIS EXISTS
A score is not an absolute measurement. It only means anything against the other
scores on the same page, and the page sorts on it. So a corpus scored by two models
is not a corpus with a bit of noise in it - it is two different scales printed in one
column, and the Rating sort compares them as though they were one.

That is what the first 39 essays were. Measured 27/08/2026:

    25/08 batch  17 essays  range 0.5-4.5  1.5 x6, 1.8 x3
    26/08 batch  22 essays  range 1.5-8.5  5.5 x6, 5.4 x4, 6.4 x3

Two causes, one per batch. The 25/08 essays were scored under the old design where
the model was asked for a verdict and a number BEFORE writing, so the number
commissioned the prose instead of describing it - see the long note at the top of
write.py. The 26/08 essays got the current second pass, but Gemini's day was already
spent when they ran, so llama-3.3-70b scored all 22 while Gemini had scored the 17
before them. Neither batch is repeating a favourite number for want of judgement:
they are two calibrations, stacked.

Re-reading eight of them with the current pass gave nine distinct values where the
live page had five, including three that moved more than two points (Montaigne on
alarm clocks 1.5 -> 3.5, Woolf on Wikipedia 6.4 -> 5.0). Repeated reads of the SAME
essay were near-identical - 5.0, 5.0, 5.0 and 5.5, 5.5, 5.5 - so the judge is stable
and the spread comes from putting it on one scale, not from asking it twice.

The verdict is rewritten alongside, because it comes from the same read and a verdict
that disagrees with its own number reads worse than either.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import _env                        # noqa: E402
import reads as reads_mod          # noqa: E402
import render                      # noqa: E402
import styles                      # noqa: E402
import write as write_stage        # noqa: E402

ESSAYS = ROOT / "data" / "essays.json"

# LEAVE WELL-READ PAGES ALONE. Rewriting a score is the right thing to do to an essay
# nobody has opened and the wrong thing to do to one people have: it changes the record
# under a reader, and the verdict - the line beside the title - is the part most likely
# to be why they remember it. Charlie asked for this on 02/09/2026.
#
# 25 is chosen against the measured traffic, not out of the air: the most-read PAGE on
# the site is the front page at 23 views, and the most-read ESSAY has 2. So nothing trips
# this today, which is the point of adding it today - the guard is in place before there
# is anything to protect, and by the time an essay passes 25 it is genuinely one people
# have read rather than one the crawler found.
#
# Scale migrations are exempt via --all, because a corpus half on one scale and half on
# another makes the Rating sort meaningless for EVERY reader, which is a worse harm than
# one popular essay's number moving. See the note above SCALE in write.py.
PROTECT_ABOVE = 25


def canonical() -> str:
    """Model AND scale. Both are part of what a score means."""
    return f"{write_stage.SCORER}/{write_stage.SCALE}"


def stale(e: dict) -> bool:
    """Not on the canonical scale.

    Absent means it predates the field. A bare model name with no scale means it was
    scored when the judge was asked for a decimal out of ten, which it answered on the
    half-point grid 70% of the time - see the note above SCALE in write.py. Both are
    stale, and both drain away without anyone resetting anything."""
    return e.get("scored_by") != canonical()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="re-read every essay")
    ap.add_argument("--limit", type=int, help="stop after N, for a day-limited tier")
    ap.add_argument("--dry", action="store_true", help="write nothing")
    args = ap.parse_args()
    _env.load()

    entries = json.loads(ESSAYS.read_text(encoding="utf-8"))
    roster = {t["id"]: t for t in styles.load()}

    targets = [e for e in entries if args.all or stale(e)]
    if args.limit:
        targets = targets[:args.limit]
    print(f"{len(targets)} of {len(entries)} essays to re-read "
          f"onto the {canonical()} scale\n")

    reads = reads_mod.load()
    if reads["asof"] == "never":
        print("  !! data/reads.json is missing - the well-read guard cannot protect\n"
              "     anything. Run tools/reads.py where the site-stats clone is.\n",
              file=sys.stderr)
    else:
        print(f"  read counts as at {reads['asof']}; "
              f"protecting anything above {PROTECT_ABOVE} views\n")

    changed, moved, protected = 0, [], 0
    for e in targets:
        n = reads_mod.views_for(render.slug(e), reads)
        if n > PROTECT_ABOVE and not args.all:
            print(f"  ..  {e['thinker']:<10} {e['object'][:22]:<22} "
                  f"{n} reads - left alone")
            protected += 1
            continue
        thinker = roster.get(e["thinker"])
        if not thinker:
            print(f"  ?? {e['thinker']} not in styles/, skipped")
            continue
        try:
            verdict, score, on_topic, by = write_stage.score_essay(
                thinker, e["object"], e["essay"])
        except Exception as exc:                     # noqa: BLE001
            # A spent quota mid-run keeps everything already repaired. Re-running
            # tomorrow picks up where it stopped, because the field records progress.
            print(f"  !! {e['thinker']}/{e['object']}: {type(exc).__name__}: {exc}"[:120])
            break
        if score is None:
            print(f"  -- {e['thinker']}/{e['object']}: no score returned, kept")
            continue
        if by != canonical():
            # The fallback answered. Writing this would swap one off-scale number for
            # another and mark it repaired, which is worse than leaving it alone.
            print(f"  -- {e['thinker']}/{e['object']}: scored by {by}, not {write_stage.SCORER}"
                  " - left for the next run")
            break
        was = e.get("score")
        print(f"  -> {e['thinker']:<10} {e['object'][:22]:<22} "
              f"{was} -> {score}   {e.get('verdict','')!r} -> {verdict!r}"
              + ("   [OFF TOPIC]" if not on_topic else ""))
        if was is not None:
            moved.append(abs(score - was))
        if not args.dry:
            e["score"], e["verdict"], e["scored_by"] = score, verdict, by
        changed += 1

    if moved:
        print(f"\nmoved by {sum(moved) / len(moved):.1f} on average, "
              f"largest {max(moved):.1f}")
    left = max(sum(stale(x) for x in entries) - (0 if args.dry else changed), 0)
    print(f"{changed} rescored, {left} still off-scale"
          + (f", {protected} left alone as well-read" if protected else ""))
    # A run that repairs NOTHING while a backlog exists is the failure worth knowing
    # about, and it is silent by construction: the step exits 0, the job goes green,
    # and the only trace is a line in a log nobody opens. That is how the mixed scale
    # went unnoticed for two days in the first place. On a spent-quota day this is
    # expected and self-correcting; on many days running it means the drain is dead
    # and the front page stays wrong. An annotation puts it on the run's own summary.
    if left and not changed and os.environ.get("GITHUB_ACTIONS"):
        print(f"::warning::rescored nothing this run; {left} essays still on the old "
              "scale. Expected on a day the free tier is spent - see the error above. "
              "If this repeats for several days the drain has stopped working.")
    if args.dry or not changed:
        return 0
    ESSAYS.write_text(json.dumps(entries, indent=2, ensure_ascii=False),
                      encoding="utf-8", newline="\n")
    render.build(entries, styles.load())
    print("archive written and pages re-rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
