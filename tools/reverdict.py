"""Re-read published essays and replace verdicts that came out as grades.

    python tools/reverdict.py            # only the ones that look like a grade
    python tools/reverdict.py --all      # every essay
    python tools/reverdict.py --dry      # show what would change, write nothing

WHY THIS EXISTS
Moving the score to a second pass fixed the numbers and broke the verdicts. Asking a
neutral reader to report what an essay expresses gets you the vocabulary of reports:
in the first batch under the new scheme, three essays came back "mild praise", two
"mixed feelings", one "vague appreciation", one "ambivalent observation". Those print
on the front page beside the title, in the writer's company, where the old batch had
"solemn humbug", "a clean limbo" and "counterfeit suffering".

The prompt now asks for the writer's own words, but a prompt only fixes the essays
written after it. This re-reads what is already published and asks again.

The score is left ALONE. It was produced by a pass that read the finished prose, which
is the design, and rescoring on a whim would churn the numbers on the front page for no
stated reason. Only the verdict is rewritten.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import render                      # noqa: E402
import styles                      # noqa: E402
import write as write_stage        # noqa: E402

ESSAYS = ROOT / "data" / "essays.json"

# The tell is a word that grades the essay instead of naming the thing. "mild praise"
# describes the review; "solemn humbug" describes LinkedIn. Anything matching gets
# another look - a false positive costs one extra call and returns the same words.
GRADEY = {
    "mild", "mixed", "vague", "ambivalent", "moderate", "slight", "somewhat",
    "praise", "critique", "criticism", "appreciation", "observation", "acceptance",
    "curiosity", "feelings", "positive", "negative", "neutral", "balanced",
    "scathing", "harsh", "favourable", "favorable", "approval", "disapproval",
    "no mention", "unclear", "n/a",
}


def is_grade(verdict: str) -> bool:
    v = (verdict or "").lower()
    if not v.strip():
        return True
    return any(w in v.split() or w in v for w in GRADEY)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="re-read every essay")
    ap.add_argument("--dry", action="store_true", help="write nothing")
    args = ap.parse_args()

    entries = json.load(open(ESSAYS, encoding="utf-8"))
    roster = {t["id"]: t for t in styles.load()}

    targets = [e for e in entries if args.all or is_grade(e.get("verdict", ""))]
    print(f"{len(targets)} of {len(entries)} essays to re-read\n")

    changed = 0
    for e in targets:
        thinker = roster.get(e["thinker"])
        if not thinker:
            print(f"  ?? {e['thinker']} not in styles/, skipped")
            continue
        try:
            verdict, _score, on_topic = write_stage.score_essay(
                thinker, e["object"], e["essay"])
        except Exception as exc:                     # noqa: BLE001
            # A spent quota mid-run should keep what it has already improved.
            print(f"  !! {e['thinker']}/{e['object']}: {type(exc).__name__}: {exc}"[:120])
            break
        if not verdict:
            print(f"  -- {e['thinker']}/{e['object']}: no verdict returned, kept")
            continue
        if verdict == e.get("verdict"):
            print(f"  == {e['thinker']:<10} {e['object'][:22]:<22} {verdict!r} unchanged")
            continue
        print(f"  -> {e['thinker']:<10} {e['object'][:22]:<22} "
              f"{e.get('verdict','')!r} -> {verdict!r}"
              + ("   [OFF TOPIC]" if not on_topic else ""))
        if not args.dry:
            e["verdict"] = verdict
        changed += 1

    print(f"\n{changed} verdict(s) rewritten")
    if args.dry or not changed:
        return 0
    json.dump(entries, open(ESSAYS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    render.build(entries, styles.load())
    print("archive written and pages re-rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
