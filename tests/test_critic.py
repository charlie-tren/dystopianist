"""The gates, and the one way a gate fails without anyone noticing.

Two things are checked here and the second is the more important.

1. THE FILLER GATES FIRE. Added 29/08/2026 after reading all 58 published essays.
   The corpus split by the model that wrote it - Gemini's 28 averaged 3.3 concrete
   anchors and 0.21 hedges, llama-3.3-70b's 30 averaged 0.3 and 0.83 - and the second
   group was costume drama with no stance. The gates catch 12 of the 58 with none of
   Gemini's among them, which is the number to keep an eye on: a gate that starts
   failing good essays is worse than no gate.

2. NO SOURCE FILE CARRIES A CONTROL BYTE. This is here because of what happened
   writing the gates. A scripted edit put a literal 0x08 into the regex where `\\b`
   was meant, so the pattern read "backspace, then 'a testament to'". It compiled. It
   imported. It ran on every essay. It matched nothing, ever, because a backspace
   character does not appear in prose - and it would have sat there looking like
   working quality control for as long as nobody counted its catches.

   The tell was that the gate caught 0 of 58 essays when the same regex, measured by
   hand minutes earlier, caught 12. A check whose output nobody compares against a
   known answer is indistinguishable from a check that does nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import critic                      # noqa: E402
import styles                      # noqa: E402

FILLER = ("stock phrase", "hedged", "appositives")


def filler_problems(text: str, thinker: dict) -> list[str]:
    return [p for p in critic.check(text, thinker, {}, "a verdict", 5.0)
            if any(k in p for k in FILLER)]


def main() -> int:
    fails: list[str] = []
    who = {t["id"]: t for t in styles.load()}
    t = who["didion"]

    # --- the gates fire on what they were written for ------------------------
    cases = [
        ("clean prose passes",
         "The room was cold and the light was the light they use in places where "
         "nobody stays. I remember the carpet, and that someone had chosen it.",
         False),
        ("stock phrase caught",
         "The machine is a testament to the age that built it, and nothing more.",
         True),
        ("hedging caught",
         "It is perhaps somewhat intriguing, though it rather seems to be the "
         "notion of a thing whose applications are not entirely clear.",
         True),
        ("appositive catalogue caught",
         "The water falls, a steady drumbeat, a soothing hum, a gentle roar; the "
         "steam rises, a misty veil, a cloudy shroud, a damp aura.",
         True),
        # Both of these were in the first draft of the stock list and taken out:
        # they read correctly in a 16th and an 18th century voice, and a gate that
        # costs a legitimate line is not worth its catch.
        ("'I must confess' still allowed",
         "And yet I must confess my own weakness in the matter, as I have before.",
         False),
        ("one hedge still allowed",
         "It is perhaps the only honest thing in the room, and it says nothing.",
         False),
    ]
    for label, text, want in cases:
        got = bool(filler_problems(text, t))
        print(f"  {'ok ' if got == want else 'FAIL'} {label}")
        if got != want:
            fails.append(f"{label}: expected {'a rejection' if want else 'clean'}, "
                         f"got {filler_problems(text, t) or 'clean'}")

    # --- no control bytes anywhere in the source ----------------------------
    # 0x07 bell, 0x08 backspace, 0x0b vertical tab, 0x0c form feed. None of these
    # belong in Python source, and each is invisible in every diff and editor.
    BAD = {7: "bell", 8: "backspace", 11: "vertical tab", 12: "form feed"}
    scanned = 0
    for f in sorted(list(ROOT.glob("*.py")) + list((ROOT / "tools").glob("*.py"))
                    + list((ROOT / "tests").glob("*.py"))):
        scanned += 1
        raw = f.read_bytes()
        hits = {BAD[b] for b in raw if b in BAD}
        if hits:
            fails.append(f"{f.name} contains {', '.join(sorted(hits))} - a regex "
                         "escape that was written as a literal control character")
    print(f"  ok  {scanned} source files carry no control bytes")

    if fails:
        print()
        for f in fails:
            print("FAIL", f, file=sys.stderr)
        return 1
    print("\nthe gates fire on filler and leave good prose alone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
