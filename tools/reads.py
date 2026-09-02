"""Per-essay pageviews, so the archive can leave well-read pages alone.

    python tools/reads.py                       # refresh from the usual site-stats clone
    python tools/reads.py --from <breakdowns.csv>
    python tools/reads.py --dry

WHY THIS IS A FILE AND NOT A FETCH
The numbers live in charlie-tren/site-stats, which is PRIVATE - the raw URL 404s without
a token - and the clone only exists on Charlie's machine. So this is a local refresh that
commits a small JSON, not something the nightly job can do for itself. That is a real
limitation and it is why `asof` is recorded: a guard reading a three-month-old file is
not protecting what it thinks it is, and rescore.py says so out loud rather than trusting
it silently.

WHAT IT IS FOR
tools/rescore.py rewrites the score and the verdict of a PUBLISHED essay. That is the
right thing to do while the archive is small and nobody has seen it, and the wrong thing
to do to a page people have read: it changes the record under them, and the verdict is
the line most likely to be the reason they remember it. Charlie asked for the guard on
02/09/2026, before it was needed rather than after, which is the only time it is cheap.

MEASURED THE SAME DAY, and worth stating plainly: 96 pageviews across every Ghostwriters
path, of which index.html has 23 and writers.html 22. The single most-read ESSAY has 2.
So this guard currently protects nothing, and that is the expected state - it is here so
that the day an essay does get read, the archive already knows not to rewrite it.
"""
from __future__ import annotations

import argparse
import csv
import collections
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

READS = ROOT / "data" / "reads.json"
DEFAULT_SOURCE = (ROOT.parent / "site-stats" / "data" / "breakdowns.csv")
PREFIX = "/ghostwriters/e/"


def load() -> dict:
    """{"asof": "...", "views": {slug: n}} - empty and dated 'never' if absent."""
    if not READS.exists():
        return {"asof": "never", "views": {}}
    return json.loads(READS.read_text(encoding="utf-8"))


def views_for(slug: str, data: dict | None = None) -> int:
    return int((data or load())["views"].get(slug, 0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", default=str(DEFAULT_SOURCE))
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"no breakdowns.csv at {src}\n"
              f"site-stats is private, so this only works where that clone exists.",
              file=sys.stderr)
        return 2

    totals = collections.Counter()
    for r in csv.DictReader(src.open(encoding="utf-8")):
        if r.get("kind") != "path":
            continue
        v = r.get("value", "")
        if not v.startswith(PREFIX) or not v.endswith(".html"):
            continue
        totals[v[len(PREFIX):-len(".html")]] += int(r.get("pageviews") or 0)

    out = {"asof": date.today().isoformat(),
           "source": "charlie-tren/site-stats data/breakdowns.csv (private)",
           "views": dict(sorted(totals.items()))}
    print(f"{len(totals)} essays with at least one read; "
          f"{sum(totals.values())} views in total")
    if totals:
        top = totals.most_common(3)
        print("  most read:", ", ".join(f"{k} ({n})" for k, n in top))
    if args.dry:
        return 0
    READS.write_text(json.dumps(out, indent=2), encoding="utf-8", newline="\n")
    print(f"wrote {READS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
