"""A well-read essay is not rewritten.

tools/rescore.py changes the score AND the verdict of a published essay. That is fine
while nobody has opened it and wrong once people have: it moves the record under a
reader, and the verdict is the line beside the title, which is the part most likely to
be why they remember the piece.

The whole difficulty with testing this is that the guard currently protects NOTHING -
the most-read essay on the site has 2 views against a threshold of 25 - so a run against
the real archive proves only that it does not crash. These tests supply the traffic the
site does not have, which is the only way to know the guard works before it matters.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import reads as reads_mod  # noqa: E402

spec = importlib.util.spec_from_file_location("rescore", ROOT / "tools" / "rescore.py")
rescore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rescore)


def main() -> int:
    fails = []
    real = reads_mod.READS
    try:
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "reads.json"
            reads_mod.READS = f

            # missing file: no crash, and everything reads as zero rather than as
            # "unknown, so probably safe to skip"
            if reads_mod.load()["asof"] != "never":
                fails.append("a missing reads.json did not report itself as 'never'")
            if reads_mod.views_for("anything") != 0:
                fails.append("a missing reads.json invented a view count")

            f.write_text(json.dumps({"asof": "2026-09-02", "views": {
                "2026-08-25-orwell-airport-lounges": 400,
                "2026-08-26-woolf-audiobooks": 25,
                "2026-08-26-wilde-dating-apps": 26,
            }}), encoding="utf-8")
            d = reads_mod.load()

            if reads_mod.views_for("2026-08-25-orwell-airport-lounges", d) != 400:
                fails.append("a real count was not read back")
            if reads_mod.views_for("never-published", d) != 0:
                fails.append("an unknown essay did not default to zero")

            # the boundary, both sides of it
            if not reads_mod.views_for("2026-08-26-wilde-dating-apps", d) > rescore.PROTECT_ABOVE:
                fails.append("26 views did not exceed a threshold of 25")
            if reads_mod.views_for("2026-08-26-woolf-audiobooks", d) > rescore.PROTECT_ABOVE:
                fails.append("exactly 25 views was treated as over the threshold")

        # the threshold has to be a real number, not a placeholder someone left at 0
        if rescore.PROTECT_ABOVE < 5:
            fails.append(f"PROTECT_ABOVE is {rescore.PROTECT_ABOVE}, which protects "
                         "almost every essay and would stall the scale migration")

        # and the migration escape hatch has to exist, or a scale change can never finish
        src = (ROOT / "tools" / "rescore.py").read_text(encoding="utf-8")
        if "and not args.all" not in src:
            fails.append("--all does not bypass the guard, so a scale migration would "
                         "stall permanently on any popular essay")
    finally:
        reads_mod.READS = real

    if fails:
        for x in fails:
            print(f"FAIL: {x}", file=sys.stderr)
        return 1
    print(f"the well-read guard holds at {rescore.PROTECT_ABOVE} views, defaults to "
          "zero when the counts are missing, and --all still completes a migration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
