"""A retry is told what the last draft failed, and a reply with text after its JSON
does not crash the run.

Added 07/10/2026. Every failed Write step in the four weeks before was the fallback
model making the same mistake three times running - 95, 102 and 97 words against a
120 floor, or 'a testament to' in all three drafts - because the retry only raised
the temperature. And on 01/10 a reply that carried text after its JSON took the run
down before a single gate was checked.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import gemini  # noqa: E402
import llm  # noqa: E402
import run  # noqa: E402

KAFKA = {"id": "kafka", "name": "Franz Kafka", "avoid": ["explain the joke"]}


def main() -> int:
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(("  ok  " if ok else "  XX  ") + name)
        fails += 0 if ok else 1

    # --- the brief for the next attempt ----------------------------------------
    t, w = run.retry_brief(["length 95 words, want 120-300"], KAFKA, "170-230")
    check("a short draft asks for a longer one", w == run.LONGER)
    t, w = run.retry_brief(["length 340 words, want 120-300"], KAFKA, "170-230")
    check("a long draft asks for a shorter one", w == run.SHORTER)

    t, w = run.retry_brief(["stock phrase: 'a testament to'"], KAFKA, "170-230")
    check("a stock phrase is added to the writer's avoid list",
          any("a testament to" in a for a in t["avoid"]))
    check("the writer's own avoid lines are kept", "explain the joke" in t["avoid"])
    check("the shared roster entry is not changed",
          KAFKA["avoid"] == ["explain the joke"])
    check("a stock phrase leaves the length alone", w == "170-230")

    t, _ = run.retry_brief(["hedged 3 times, so it takes no position"], KAFKA, "170-230")
    check("hedging is named for the next draft", any(a.startswith("hedge") for a in t["avoid"]))

    t, w = run.retry_brief(["mentions a year"], KAFKA, "170-230")
    check("a failure with no brief change leaves everything as it was",
          t is KAFKA and w == "170-230")

    # The avoid lines reach the prompt the next draft is written from.
    import write
    thinker = {**run.retry_brief(["stock phrase: 'relentless pursuit'"], {
        "id": "orwell", "name": "George Orwell", "dates": "1903-1950",
        "note": "plain", "shot": "Sample.", "avoid": []}, "170-230")[0]}
    check("the phrase is in the prompt the retry sends",
          "relentless pursuit" in write.build_prompt(thinker, "the washing machine", "170-230"))

    # --- a reply with something after its JSON --------------------------------
    raw = ('{"essay": "The Master said, it is so.", "verdict": "x"} '
           'Here is the essay you asked for {and more}')
    try:
        got = gemini.extract_json(raw)
        check("the first complete object is taken, the trailing text ignored",
              got.get("essay") == "The Master said, it is so.")
    except Exception as e:  # noqa: BLE001
        check(f"the first complete object is taken (raised {type(e).__name__})", False)
    try:
        check("llm's reader takes it too",
              llm.extract_json(raw).get("essay") == "The Master said, it is so.")
    except Exception as e:  # noqa: BLE001
        check(f"llm's reader takes it too (raised {type(e).__name__})", False)

    print("all retry checks pass" if not fails else f"{fails} FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
