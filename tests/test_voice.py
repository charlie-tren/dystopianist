"""The balance test the idea lives or dies by: are the thinkers still distinct?

Not a per-essay gate - see the note in critic.py for why that failed. This asks the
only question that matters at corpus level: taking everything each thinker has
published, do their averages stay apart? If the fleet collapses into one register,
this goes red long before anyone reads two pages and notices.
"""
from __future__ import annotations

import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import voice  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# Below this two thinkers are writing the same way. The eleven reference samples sit
# at 1.02 for their closest pair (Montaigne/Twain, which is fair - both ramble
# genially in the first person), so anything under half that is a real collapse.
FLOOR = 0.45
# A WARNING BAND, because this gate had no middle. On 09/09/2026 it went from silent
# green to a red job in one night - dickinson and nietzsche at 0.44 - and killed the
# 18:00 heartbeat run. It passed again the next night and has passed every night
# since (56 of the last 60 runs green, the other three from August), which is worse
# than a clean break: the measurement drifts around its own threshold and nobody
# sees it move until it crosses.
#
# The margin is thin. On 18/09/2026 the closest pair was dickens / thompson at 0.47,
# two hundredths clear, and it is a DIFFERENT pair from the one that failed - so this
# is not one bad pairing, it is the fleet slowly compacting.
#
# A warning exits 0 on purpose. A gate that cries wolf gets switched off, and there
# is nothing to do about 0.50 tonight that was not already true yesterday - but it
# gives the revoice queue a reason to run before the build goes red, and it makes the
# drift legible in a log somebody already reads.
WARN = 0.55
NEAR = 3              # how many of the closest pairs to print, so drift has a shape
MIN_EACH = 2          # a thinker needs a couple of essays before an average means much


def main() -> int:
    archive = ROOT / "data" / "essays.json"
    if not archive.exists():
        print("no essays yet - nothing to check")
        return 0
    entries = json.loads(archive.read_text(encoding="utf-8"))

    by = defaultdict(list)
    for e in entries:
        by[e["thinker"]].append(e["essay"])
    ready = {k: " ".join(v) for k, v in by.items() if len(v) >= MIN_EACH}
    if len(ready) < 2:
        print(f"only {len(ready)} thinker(s) with {MIN_EACH}+ essays - too early to judge")
        return 0

    worst, pair = voice.divergence(ready)
    print(f"{len(ready)} thinkers compared; closest pair {pair[0]} / {pair[1]} "
          f"at {worst:.2f} (floor {FLOOR}, warn {WARN})")

    # The runners-up. One pair on the floor is a pairing; three pairs bunched under
    # the warning line is the corpus compacting, and the report should tell those
    # two apart rather than reporting a single number either way.
    ids = sorted(ready)
    pairs = sorted(
        (voice.divergence({a: ready[a], b: ready[b]})[0], a, b)
        for i, a in enumerate(ids) for b in ids[i + 1:]
    )[:NEAR]
    print("  closest: " + ", ".join(f"{a}/{b} {d:.2f}" for d, a, b in pairs))
    for tid in sorted(ready):
        fp = voice.fingerprint(ready[tid])
        print(f"  {tid:10} sent={fp['mean_sent']:5.1f} latinate={fp['latinate']:.3f} "
              f"first={fp['first']:.3f} second={fp['second']:.3f}")
    if worst < FLOOR:
        print(f"\nFAILED: {pair[0]} and {pair[1]} have converged ({worst:.2f} < {FLOOR}). "
              "Their samples need to pull further apart - a longer prompt will not fix this.")
        return 1
    if worst < WARN:
        print(f"\nWARNING: {pair[0]} and {pair[1]} are at {worst:.2f} - inside the "
              f"warning band ({WARN}) and only {worst - FLOOR:.2f} clear of the floor. "
              "Not a failure. Run tools/revoice.py on the pairs above before it is one.")
        return 0
    print("\nvoices are still distinct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
