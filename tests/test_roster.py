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

# --- objects.yaml shortlists -------------------------------------------------
objs = yaml.safe_load((ROOT / "config" / "objects.yaml").read_text(encoding="utf-8"))
for o in objs["objects"]:
    unknown = [w for w in (o.get("writers") or []) if w not in ids]
    if unknown:
        failures.append(f"{o['name']!r} shortlists writers not in styles/: "
                        f"{', '.join(unknown)}")

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
