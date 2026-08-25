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
    print(f"{len(ready)} thinkers compared; closest pair {pair[0]} / {pair[1]} at {worst:.2f}")
    for tid in sorted(ready):
        fp = voice.fingerprint(ready[tid])
        print(f"  {tid:10} sent={fp['mean_sent']:5.1f} latinate={fp['latinate']:.3f} "
              f"first={fp['first']:.3f} second={fp['second']:.3f}")
    if worst < FLOOR:
        print(f"\nFAILED: {pair[0]} and {pair[1]} have converged ({worst:.2f} < {FLOOR}). "
              "Their samples need to pull further apart - a longer prompt will not fix this.")
        return 1
    print("\nvoices are still distinct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
