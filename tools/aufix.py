"""Put the American spellings right, in the essays that should not have them.

    python tools/aufix.py --dry     # list what would change, write nothing
    python tools/aufix.py           # write data/essays.json

WHY THIS EXISTS
The site is Australian English and the models spell American by default. Measured over
the 66 published essays: nine words across seven writers - Orwell and Tolstoy and
Russell on "labor", Montaigne and Russell on "neighbor", Kafka on "colored" and
"mechanized", Nietzsche on "anesthesia", Wilde on "civilized" - plus five verdicts.

WHY IT IS KEYED ON THE WRITER
Eleven of the twenty-four are American. Twain writing "labor" is correct pastiche and
this must never touch it; Orwell writing "labor" is a fault of exactly the same kind as
a date or a modern word. critic.AMERICAN holds the split and this script defers to it,
so there is one list rather than two that drift.

The verdicts are different and get corrected whoever the writer is: a verdict is the
SITE speaking, printed in a column beside sixty-five others, and a column carrying both
"theater" and "theatre" reads as a mistake rather than as characterisation.

WHY NO MODEL
A spelling is not a judgement. Asking a model to fix one would cost a free-tier call,
take a night, and introduce the possibility of it changing something else. This is a
substitution, it is reversible, and the essay says the same thing afterwards. The
matching gate in critic.py stops it coming back, so this runs once and then never
catches anything.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import critic                      # noqa: E402
import render                      # noqa: E402
import styles                      # noqa: E402

ESSAYS = ROOT / "data" / "essays.json"


def swap(text: str) -> tuple[str, list[str]]:
    """Replace every American spelling, keeping the case of what was there.

    Case matters because these appear at the start of sentences: a blind lowercase
    substitution would leave "Labor" as "labour" mid-page, which is a second defect
    introduced by the fix for the first."""
    changed = []

    def one(m):
        found = m.group(0)
        au = critic.US_SPELLING[found.lower()]
        if found[0].isupper():
            au = au[0].upper() + au[1:]
        changed.append(f"{found} -> {au}")
        return au

    return critic._US.sub(one, text or ""), changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="write nothing")
    args = ap.parse_args()

    entries = json.loads(ESSAYS.read_text(encoding="utf-8"))
    roster = {t["id"]: t for t in styles.load()}
    essays_fixed = verdicts_fixed = 0

    for e in entries:
        # The prose only where the writer was not American. See critic.AMERICAN.
        if e["thinker"] not in critic.AMERICAN:
            new, changed = swap(e["essay"])
            if changed:
                print(f'  {e["thinker"]:<11}{e["object"][:24]:<25} '
                      + ", ".join(changed))
                e["essay"] = new
                essays_fixed += 1
        # The verdict always.
        new, changed = swap(e.get("verdict", ""))
        if changed:
            print(f'  {e["thinker"]:<11}verdict{"":<18} ' + ", ".join(changed))
            e["verdict"] = new
            verdicts_fixed += 1

    print(f"\n{essays_fixed} essays and {verdicts_fixed} verdicts corrected")

    # Prove it against the gate rather than against this script's own count: a
    # substitution that missed a form would still report a happy number here.
    left = 0
    for e in entries:
        if e["thinker"] not in critic.AMERICAN:
            left += len(critic.us_spellings(e["essay"]))
        left += len(critic.us_spellings(e.get("verdict", "")))
    print(f"critic still finds {left} (want 0)")
    # And the American half must be untouched, or the fix has become a different bug.
    kept = sum(len(critic.us_spellings(e["essay"]))
               for e in entries if e["thinker"] in critic.AMERICAN)
    print(f"{kept} American spellings left standing in American writers, as intended")
    if left:
        print("REFUSING to write: the gate still sees faults", file=sys.stderr)
        return 1

    if args.dry:
        print("dry run, nothing written")
        return 0
    if essays_fixed or verdicts_fixed:
        ESSAYS.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8", newline="\n")
        render.build(entries, styles.load())
        print("essays.json written and the site rebuilt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
