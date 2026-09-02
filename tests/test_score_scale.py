"""The judge answers out of 100; the page prints out of 10.

The bug this exists to prevent was nearly shipped on 02/09/2026. The obvious way to
handle two possible scales is "divide by ten only if it is over ten" - and that is a
silent inverter, because the scales OVERLAP at the bottom. Orwell on airport lounges,
the most contemptuous essay on the site, scored 8 out of 100. Under that rule it would
have published as 8.0 out of 10, the warmest number on the front page.

No arithmetic can separate 8-out-of-100 from 8-out-of-10. So the contract is enforced
rather than inferred: a WHOLE number was asked for, and a fractional answer is a scorer
that did not do as it was told. That returns None, which critic.py already fails, so the
essay is re-rolled instead of published against an uninterpretable number.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import llm                          # noqa: E402
import write as write_stage         # noqa: E402

THINKER = {"name": "George Orwell", "dates": "1903-1950"}


def _score_returning(payload):
    """Run score_essay with the model stubbed to return `payload`."""
    real = llm.generate
    llm.generate = lambda *a, **k: ('{"verdict": "a carpeted box", "score": %s,'
                                    ' "on_topic": true}' % payload, "gemini")
    try:
        return write_stage.score_essay(THINKER, "airport lounges", "Some prose.")
    finally:
        llm.generate = real


def main() -> int:
    fails = []

    # The case that would have inverted: 8 means 8/100, not 8/10.
    _, score, _, by = _score_returning("8")
    if score != 0.8:
        fails.append(f"a raw 8 became {score}, want 0.8 - the demolition inverter")
    if by != f"gemini/{write_stage.SCALE}":
        fails.append(f"scored_by is {by!r}, want the model AND the scale")

    for raw, want in (("0", 0.0), ("47", 4.7), ("87", 8.7), ("100", 10.0)):
        _, score, _, _ = _score_returning(raw)
        if score != want:
            fails.append(f"raw {raw} became {score}, want {want}")

    # A fractional answer is a broken contract, not a number to rescue.
    for raw in ("8.5", "0.8", "4.75"):
        _, score, _, _ = _score_returning(raw)
        if score is not None:
            fails.append(f"raw {raw} became {score}, want None so the gate re-rolls it")

    for raw in ('"banana"', "null"):
        _, score, _, _ = _score_returning(raw)
        if score is not None:
            fails.append(f"raw {raw} became {score}, want None")

    # And the gate must actually reject a None, or returning None achieves nothing.
    import critic
    problems = critic.check("word " * 200, THINKER, {}, verdict="a carpeted box",
                            score=None, on_topic=True)
    if not any("score" in p for p in problems):
        fails.append("critic.check accepts score=None, so a broken scale would publish")

    if fails:
        for f in fails:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print(f"the scale holds: asked out of {write_stage.SCALE}, printed out of 10, "
          "and a fractional answer is refused rather than guessed at")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
