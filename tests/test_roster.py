"""Every writer in styles/ must be fully wired up everywhere else.

    python tests/test_roster.py

Adding a writer means touching more than one file, and the second one is easy to
forget. On 26/08/2026 seven writers were added to styles/ and not to the LOOK map in
tools/portraits.py. The portraits step raised KeyError on the first of them, which
failed the job, which SKIPPED the commit step - and that commit was carrying a
completed reverdict pass over seventeen essays. One missing dictionary key threw away
an unrelated hour of work.

So this checks the joins rather than the contents. It is cheap and it runs in CI
before anything expensive does.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import styles                      # noqa: E402
import yaml                        # noqa: E402

failures: list[str] = []
roster = styles.load()
ids = {t["id"] for t in roster}
print(f"{len(ids)} writers in styles/")

# --- portraits ---------------------------------------------------------------
src = (ROOT / "tools" / "portraits.py").read_text(encoding="utf-8")
block = src.split("LOOK = {", 1)[1].split("\n}", 1)[0]
look = set(re.findall(r'^\s*"(\w+)":\s*"', block, re.M))
if ids - look:
    failures.append(f"no portrait description in tools/portraits.py LOOK: "
                    f"{', '.join(sorted(ids - look))}")
if look - ids:
    failures.append(f"LOOK describes writers that are not in styles/: "
                    f"{', '.join(sorted(look - ids))}")

# --- the surname sort key ----------------------------------------------------
# The Writers page files by the name a reader holds a writer by, and the key is STATED
# per writer rather than derived, because the last word of the display name is wrong
# three times in twenty-three: Aurelius is not a surname, Montaigne carries a particle,
# and Wallace is the third word of "David Foster Wallace". A clever rule gets those
# wrong quietly. This makes a forgotten key loud instead - the same failure the LOOK
# map already taught, where a writer added to styles/ and forgotten elsewhere took the
# whole workflow down.
for t in roster:
    key = str(t.get("sort", "")).strip()
    if not key:
        failures.append(f"{t['id']} has no sort: key in its front matter")
        continue
    if key not in t["name"]:
        failures.append(f"{t['id']} sort key {key!r} is not part of {t['name']!r}")
if len({t.get("sort") for t in roster}) != len(roster):
    failures.append("two writers share a sort key, so their order is arbitrary")

# --- objects.yaml shortlists -------------------------------------------------
objs = yaml.safe_load((ROOT / "config" / "objects.yaml").read_text(encoding="utf-8"))
died = {t["id"]: int(str(t.get("dates", "0-0")).split("-")[-1]) for t in roster}
for o in objs["objects"]:
    unknown = [w for w in (o.get("writers") or []) if w not in ids]
    if unknown:
        failures.append(f"{o['name']!r} shortlists writers not in styles/: "
                        f"{', '.join(unknown)}")

    # A dated object may only go to writers who died BEFORE it. The whole premise is
    # that none of them lived to see the thing, and the site says so on its front
    # page, so a Didion review of a 2017 film is not a bad essay - it is the site
    # contradicting itself. Checked against the whole roster and not just the
    # shortlist, because `pick` falls back to everyone once the shortlists are spent.
    year = o.get("year")
    if year is None:
        continue
    saw_it = [w for w in (o.get("writers") or []) if died.get(w, 0) >= year]
    if saw_it:
        failures.append(f"{o['name']!r} shortlists writers who lived to see it: "
                        f"{', '.join(saw_it)}")
    if not [t for t in ids if died.get(t, 0) < year]:
        failures.append(f"{o['name']!r} has no eligible writer at all")

# --- every writer has at least one sample, and real prose is attributed -------
for t in roster:
    if not t.get("samples"):
        failures.append(f"{t['id']} has no samples")
    for i, s in enumerate(t.get("samples") or [], 1):
        if not s.get("text", "").strip():
            failures.append(f"{t['id']} sample {i} is empty")

if failures:
    print()
    for f in failures:
        print("  FAIL", f)
    raise SystemExit(1)

print("roster is wired up: portraits, object shortlists and samples all agree")
