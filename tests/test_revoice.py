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
# A voice with no `model:` line, so the fixtures test the fallback rules alone.
T = "adams"
GOOD = ("The machine hums in the corner of the scullery and eats an afternoon that "
        "used to belong to three women with red arms. " * 6)
BAD = ("It is a testament to the relentless pursuit of convenience. " * 12)


def entry(essay, thinker=T):
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


def the_fallbacks_work_is_queued_even_when_it_passes(fails):
    """The widening, and the reason for it. Orwell on airport security cleared every
    gate and had him calling it "a small price to pay". Clean prose from the fallback
    is queued; identical prose from Gemini is not, or the queue never converges."""
    weak = entry(GOOD)
    weak["provider"] = "cloudflare"
    if not revoice.listed(weak, ROSTER[T]):
        fails.append("a clean essay by the fallback model was not queued")
    if revoice.faults(weak, ROSTER[T]):
        fails.append("the fixture is not clean, so this proves nothing")
    good = dict(weak, provider=write_stage.SCORER)
    if revoice.listed(good, ROSTER[T]):
        fails.append("a clean essay by Gemini was queued, so the drain cannot converge")
    print("  clean prose: queued from the fallback, not queued from Gemini")


def only_prose_faults_put_an_essay_on_the_list(fails):
    """A missing score is a scoring fault. Rewriting the prose would not fix it, and
    an essay on this list for that reason would be rewritten every night forever."""
    e = entry(GOOD)
    e["score"] = None
    got = revoice.faults(e, ROSTER[T])
    if any(p.startswith(("score ", "verdict ")) for p in got):
        fails.append(f"a scoring fault reached the rewrite list: {got}")
    if got:
        fails.append(f"clean prose was listed anyway: {got}")
    print("  a missing score does not put clean prose on the rewrite list")


def a_failing_essay_is_on_the_list(fails):
    """The control. Without this the check above passes on a gate that never fires."""
    got = revoice.faults(entry(BAD), ROSTER[T])
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


def a_rewrite_whose_verdict_is_a_grade_is_re_read(fails):
    """Rewriting the essay rewrites its verdict, so this path can put "mild praise" on
    an essay that was fine. It gets one more reading, then the rewrite is refused."""
    rereads = []

    def stub(thinker, obj, **kw):
        return GOOD, "mild praise", 5.0, write_stage.SCORER, True, "gemini"

    def score_stub(thinker, obj, essay):
        rereads.append(essay)
        return "cautious observation", 5.0, True, "gemini"   # a grade again

    real = write_stage.score_essay
    write_stage.score_essay = score_stub
    try:
        run(stub, [entry(BAD)])
    finally:
        write_stage.score_essay = real
    # Exactly one. Zero means the grade went to the page; more than one means it
    # loops, which on a spent free tier is the expensive way to fail.
    if len(rereads) != 1:
        fails.append(f"the scoring pass ran {len(rereads)} times, want exactly 1")
    print(f"  a grade-ish verdict is re-read {len(rereads)}x, then the rewrite is refused")

    # And the control: a verdict that is NOT a grade must not trigger a re-read at all.
    rereads.clear()

    def clean_stub(thinker, obj, **kw):
        return GOOD, "upholstered doom", 5.0, write_stage.SCORER, True, "gemini"

    write_stage.score_essay = score_stub
    try:
        run(clean_stub, [entry(BAD)])
    finally:
        write_stage.score_essay = real
    if rereads:
        fails.append("a good verdict was re-read anyway, which spends a call for nothing")
    print("  a verdict that is not a grade is left alone")


def an_essay_by_the_wrong_primary_is_queued(fails):
    """A styles `model:` line names who writes that voice. Claude's essay for a
    Gemini voice is queued; the same essay by Gemini is not, and a voice with no
    model line queues neither."""
    pinned = dict(ROSTER[T], model="gemini")
    unpinned = {k: v for k, v in ROSTER[T].items() if k != "model"}
    by_claude = dict(entry(GOOD), provider="claude")
    by_gemini = dict(entry(GOOD), provider="gemini")
    if not revoice.listed(by_claude, pinned):
        fails.append("Claude's essay for a Gemini-pinned voice was not queued")
    if revoice.listed(by_gemini, pinned):
        fails.append("Gemini's essay for a Gemini-pinned voice was queued")
    if revoice.listed(by_claude, unpinned):
        fails.append("Claude's essay for an unpinned voice was queued")
    print("  wrong primary for a pinned voice: queued; right one or unpinned: not")


def an_essay_older_than_its_samples_is_queued(fails):
    """`samples_from:` queues essays written before it, and a rewrite dated after
    it leaves the list."""
    voice = dict(ROSTER[T], samples_from="2026-11-12")
    old = dict(entry(GOOD), provider="gemini", generated="2026-10-01T03:00:00+00:00")
    new = dict(old, generated="2026-11-13T03:00:00+00:00")
    redone = dict(old, revoiced="2026-11-12")
    if not revoice.listed(old, voice):
        fails.append("an essay older than its samples was not queued")
    if revoice.listed(new, voice) or revoice.listed(redone, voice):
        fails.append("an essay written or rewritten after the samples was queued")
    print("  older than the samples: queued; written or rewritten since: not")


def it_refuses_the_other_primarys_rewrite(fails):
    """If the pinned model does not answer and the other primary does, nothing is
    accepted: that rewrite would put the essay straight back on the list."""
    accepted = {}
    real = dict(ROSTER[T])
    ROSTER[T]["model"] = "gemini"
    revoice_roster = revoice.styles.load

    def stub(thinker, obj, **kw):
        return GOOD, "a clean verdict", 5.0, "claude", True, "claude"

    def roster():
        return [dict(t, model="gemini") if t["id"] == T else t for t in revoice_roster()]

    revoice.styles.load = roster
    try:
        # BAD, so it is queued by a gate too: the refusal is then tested on its own.
        e = dict(entry(BAD), provider="claude")
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run(stub, [e])
        if "->" in buf.getvalue():
            accepted["yes"] = True
    finally:
        revoice.styles.load = revoice_roster
        ROSTER[T].clear(); ROSTER[T].update(real)
    if accepted:
        fails.append("Claude's rewrite was accepted for a Gemini-pinned voice")
    print("  the other primary's rewrite is refused for a pinned voice")


def main() -> int:
    fails: list[str] = []
    for check in (an_essay_by_the_wrong_primary_is_queued,
                  an_essay_older_than_its_samples_is_queued,
                  it_refuses_the_other_primarys_rewrite,
                  the_fallbacks_work_is_queued_even_when_it_passes,
                  a_rewrite_whose_verdict_is_a_grade_is_re_read,
                  only_prose_faults_put_an_essay_on_the_list,
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
