"""The pairing must cover every subject before it gives any subject a second essay.

    python tests/test_pick.py

On 26/08/2026 five films were added to config/objects.yaml. Two nights later all five
were still on nought, because the rotation only ever balanced WRITERS: `--until N`
topped up anyone short and the daily pick then chose at random among the shortlisted
pairs, which a new subject can lose for weeks. A subject on nought is not a queue,
it is an empty shelf on a site whose whole index is the list of subjects.

So this asserts the PREFERENCE, not the outcome of one draw - pick() is random, and a
test that draws once would pass by luck roughly half the time.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import run                             # noqa: E402
import styles                          # noqa: E402

failures: list[str] = []
thinkers = styles.load()
objects = run.load("objects.yaml")["objects"]

# --- an uncovered subject wins, every time ------------------------------------
# One subject written about, everything else at nought: 200 draws should never
# return the covered one while 19 others are empty.
past = [{"thinker": "kafka", "object": objects[0]["name"]}]
random.seed(1)
strays = {pick[1] for pick in (run.pick(thinkers, objects, past) for _ in range(200))
          if pick[1] == objects[0]["name"]}
if strays:
    failures.append(f"picked the only covered subject {objects[0]['name']!r} while "
                    f"{len(objects) - 1} were at nought")

# --- and the eligibility rule still holds inside that preference ---------------
# The coverage preference must not become a back door around the premise: a writer
# still may not be set on a film that predates their death.
died = {t["id"]: int(str(t.get("dates", "0-0")).split("-")[-1]) for t in thinkers}
by_name = {o["name"]: o for o in objects}
random.seed(2)
for _ in range(300):
    tid, obj = run.pick(thinkers, objects, past)
    year = by_name[obj].get("year")
    if year is not None and died[tid] >= year:
        failures.append(f"{tid} (died {died[tid]}) was set on {obj!r}")
        break

# --- with everything covered it falls back to the shortlists -------------------
# Same guarantee as before the change: the strong matchups are not left to the
# shuffle once coverage is satisfied.
all_covered = [{"thinker": "kafka", "object": o["name"]} for o in objects]
shortlists = {(w, o["name"]) for o in objects for w in (o.get("writers") or [])}
random.seed(3)
off = [p for p in (run.pick(thinkers, objects, all_covered) for _ in range(200))
       if p not in shortlists]
if off:
    failures.append(f"{len(off)} of 200 draws ignored the shortlists while "
                    f"{len(shortlists)} shortlisted pairs were unused")

if failures:
    print()
    for f in failures:
        print("  FAIL", f)
    raise SystemExit(1)

print(f"pairing covers subjects first: {len(objects)} subjects, "
      f"{len(thinkers)} writers, eligibility held over 500 draws")
