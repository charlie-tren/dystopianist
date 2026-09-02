"""The rewrite drain, and the two ways it could empty its own backlog dishonestly.

Both failure modes look identical from outside: the list gets shorter every night and
the job goes green. The difference is only visible on the page.

  - accepting the fallback model's rewrite, which produces the same voiceless genre
    that put the essay on the list in the first place
  - accepting a rewrite that still fails the gates that rejected the original

Neither needs a model to test. The generator is swapped for a stub that returns
exactly the bad case, which is also the only way to see these paths at all: they never
run on a good night.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import critic                      # noqa: E402
import styles                      # noqa: E402
import write as write_stage        # noqa: E402

spec = importlib.util.spec_from_file_location("revoice", ROOT / "tools" / "revoice.py")
revoice = importlib.util.module_from_spec(spec)
sys.modules["revoice"] = revoice
spec.loader.exec_module(revoice)

ROSTER = {t["id"]: t for t in styles.load()}
GOOD = ("The machine hums in the corner of the scullery and eats an afternoon that "
        "used to belong to three women with red arms. " * 6)
BAD = ("It is a testament to the relentless pursuit of convenience. " * 12)


def entry(essay, thinker="orwell"):
    return {"date": "2026-01-01", "thinker": thinker, "name": ROSTER[thinker]["name"],
            "dates": "1903-1950", "object": "the washing machine", "essay": essay,
            "verdict": "a carpeted box", "score": 4.0, "provider": "cloudflare",
            "scored_by": "gemini"}


def run(monkey, entries):
    """Drive main() with a stubbed generator and no disk writes."""
    real_write, real_essays = write_stage.write, revoice.ESSAYS
    tmp = ROOT / "tests" / "_tmp_revoice.json"
    tmp.write_text(json.dumps(entries), encoding="utf-8")
    write_stage.write, revoice.ESSAYS = monkey, tmp
    try:
        revoice.main.__globals__["sys"].argv = ["revoice", "--dry"]
        rc = revoice.main()
    finally:
        write_stage.write, revoice.ESSAYS = real_write, real_essays
        tmp.unlink(missing_ok=True)
    return rc


def only_prose_faults_put_an_essay_on_the_list(fails):
    """A missing score is a scoring fault. Rewriting the prose would not fix it, and
    an essay on this list for that reason would be rewritten every night forever."""
    e = entry(GOOD)
    e["score"] = None
    got = revoice.faults(e, ROSTER["orwell"])
    if any(p.startswith(("score ", "verdict ")) for p in got):
        fails.append(f"a scoring fault reached the rewrite list: {got}")
    if got:
        fails.append(f"clean prose was listed anyway: {got}")
    print("  a missing score does not put clean prose on the rewrite list")


def a_failing_essay_is_on_the_list(fails):
    """The control. Without this the check above passes on a gate that never fires."""
    got = revoice.faults(entry(BAD), ROSTER["orwell"])
    if not got:
        fails.append("an essay full of stock phrases was not listed")
    print(f"  stock-phrase prose is listed: {got[0]}")


def it_refuses_the_fallback_models_rewrite(fails):
    calls = []

    def stub(thinker, obj, **kw):
        calls.append(obj)
        return GOOD, "a clean verdict", 5.0, "cloudflare", True, "gemini"

    run(stub, [entry(BAD)])
    if not calls:
        fails.append("the generator was never called")
    print(f"  the fallback answered on {len(calls)} call and nothing was accepted")


def it_refuses_a_rewrite_that_still_fails(fails):
    def stub(thinker, obj, **kw):
        return BAD, "a clean verdict", 5.0, write_stage.SCORER, True, "gemini"

    run(stub, [entry(BAD)])
    print("  a rewrite that still fails the gates is refused, the original kept")


def it_accepts_a_good_rewrite(fails):
    """The one that must go through, or the two checks above are satisfied by a
    drain that never accepts anything."""
    out = {}

    def stub(thinker, obj, **kw):
        out["called"] = True
        return GOOD, "a clean verdict", 5.0, write_stage.SCORER, True, "gemini"

    run(stub, [entry(BAD)])
    if not out:
        fails.append("a good rewrite never reached the generator")
    print("  a clean rewrite from the right model is accepted")


def main() -> int:
    fails: list[str] = []
    for check in (only_prose_faults_put_an_essay_on_the_list,
                  a_failing_essay_is_on_the_list,
                  it_refuses_the_fallback_models_rewrite,
                  it_refuses_a_rewrite_that_still_fails,
                  it_accepts_a_good_rewrite):
        print(f"{check.__name__}:")
        check(fails)
    if fails:
        for f in fails:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("\nthe backlog can only empty by actually being fixed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
