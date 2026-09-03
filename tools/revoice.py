"""Rewrite published essays that have no voice in them, one small batch a night.

    python tools/revoice.py                # only the ones today's gates reject
    python tools/revoice.py --limit 3      # stop after N, for a day-limited free tier
    python tools/revoice.py --dry          # show what would change, write nothing
    python tools/revoice.py --list         # just print the backlog and stop

WHY THIS EXISTS
The filler gates in critic.py were written on 29/08/2026 and only apply to essays
written after them. Run over what was already published, they reject twelve - and all
twelve were written by the fallback model, none by Gemini. That is not a marginal
split, it is the whole signal: llama-3.3-70b's essays are not worse pastiche, they are
a different genre, costume drama with no stance, hedged into saying nothing.

The queue is everything the gates reject PLUS everything the fallback wrote, because
the gates catch only twelve of its twenty-eight. See listed() for why that is
provenance rather than a new heuristic. Gate failures go first.

Charlie found it from the other end, playing the guessing game: "weaker-model essays
are close to unguessable because they have no voice at all". A gate that only protects
the future leaves that on the page forever, and the essays are the site.

THE THREE RULES THAT MAKE THIS SAFE

1. It will not accept the fallback model's work. Rewriting a voiceless essay with the
   model that wrote it is a free-tier call spent to change nothing. If the fallback
   answers, the essay is left exactly as it was and the run stops, the same way
   rescore.py stops rather than writing an off-scale number.

2. The replacement has to PASS the gates that rejected the original. Otherwise this
   swaps one failing essay for another and marks it repaired, which is worse than
   leaving it: the backlog would empty while the page stayed wrong.

3. The well-read guard, exactly as rescore.py has it. A rewrite keeps the URL - the
   slug is date, writer and object, none of which change - so anyone who has read that
   page finds different prose at the same address. Above PROTECT_ABOVE views it is
   left alone.

The score and verdict are rewritten with the essay, and that is deliberate rather than
churn: they describe prose that no longer exists.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# tools/ as well as the repo root. Run as `python tools/revoice.py` it is already
# sys.path[0], but a test importing this by path gets neither, and `reads` lives here.
sys.path.insert(0, str(ROOT / "tools"))

import _env                        # noqa: E402
import critic                      # noqa: E402
import reads as reads_mod          # noqa: E402
import render                      # noqa: E402
import styles                      # noqa: E402
import write as write_stage        # noqa: E402

_env.load()

ESSAYS = ROOT / "data" / "essays.json"

# Same threshold as tools/rescore.py, and for the same reason: set against measured
# traffic rather than a round number. The busiest page on the site had 23 views and the
# busiest essay 2, so this protects nothing today and is in place for when it does.
PROTECT_ABOVE = 25

# The score and verdict complaints are not about the prose - a missing score is a
# scoring fault and rewriting the essay would not fix it. Only prose faults put an
# essay on this list.
NOT_PROSE = ("score ", "verdict ")


def faults(entry: dict, thinker: dict) -> list[str]:
    """Every reason today's gates would refuse to publish this essay."""
    return [p for p in critic.check(entry["essay"], thinker, {},
                                    verdict=entry.get("verdict", "-"),
                                    score=entry.get("score"), on_topic=True)
            if not p.startswith(NOT_PROSE)]


def listed(entry: dict, thinker: dict) -> list[str]:
    """Why this essay is on the rewrite list: a gate it fails, or who wrote it.

    PROVENANCE IS A REASON ON ITS OWN, added 03/09/2026 and worth the argument.
    The gates catch twelve of the twenty-eight essays the fallback has written, and
    the sixteen that pass are not thereby fine. The one published on 02/09 cleared
    every gate and has Orwell calling airport security "a small price to pay for the
    reassurance that we are safe from harm" - which is not a weak essay by Orwell,
    it is the opposite of Orwell, in sixteen uses of "we" and three of "and yet".

    The alternative was a new prose gate, and it was NOT written, deliberately. A gate
    built to catch that one essay is fitted to it: "and yet twice" catches two of
    twenty-eight, "we eight times" catches two good Gemini essays as well. Measuring
    candidates against the corpus is what killed the concreteness gate in critic.py,
    and the same measurement kills these.

    What is NOT fitted to one essay is the provider, which three separate measurements
    have now split the same way - 3.3 concrete anchors an essay against 0.3, hedges
    0.21 against 0.83, and after the prompt reorder 0.40 against 1.20. The field is
    already on every entry and needs no heuristic at all.

    It converges by construction: a rewrite is only accepted from Gemini, so a
    rewritten essay leaves this list on the way out.
    """
    why = faults(entry, thinker)
    if entry.get("provider") and entry["provider"] != write_stage.SCORER:
        why.append(f'written by {entry["provider"]}, the fallback model')
    return why


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="stop after N rewrites")
    ap.add_argument("--dry", action="store_true", help="write nothing")
    ap.add_argument("--list", action="store_true", help="print the backlog and stop")
    args = ap.parse_args()

    entries = json.loads(ESSAYS.read_text(encoding="utf-8"))
    roster = {t["id"]: t for t in styles.load()}

    backlog = [e for e in entries
               if e["thinker"] in roster and listed(e, roster[e["thinker"]])]
    # Worst first: an essay that fails a gate is a defect on the page today, where one
    # that merely came from the fallback is a quality ceiling. On a night that gets two
    # calls, the defects should have them.
    backlog.sort(key=lambda e: not faults(e, roster[e["thinker"]]))
    gated = sum(1 for e in backlog if faults(e, roster[e["thinker"]]))
    print(f"{len(backlog)} of {len(entries)} published essays queued: "
          f"{gated} failing a gate, {len(backlog) - gated} written by the fallback")
    for e in backlog:
        print(f'  {(e.get("provider") or "?"):<11}{e["thinker"]:<11}'
              f'{e["object"][:24]:<25} {"; ".join(listed(e, roster[e["thinker"]]))}')
    if args.list:
        return 0
    print()

    targets = backlog[:args.limit] if args.limit else backlog

    reads = reads_mod.load()
    if reads["asof"] == "never":
        print("  !! data/reads.json is missing - the well-read guard cannot protect\n"
              "     anything. Run tools/reads.py where the site-stats clone is.\n",
              file=sys.stderr)
    else:
        print(f"  read counts as at {reads['asof']}; "
              f"protecting anything above {PROTECT_ABOVE} views\n")

    done, protected, refused = 0, 0, 0
    for e in targets:
        thinker = roster[e["thinker"]]
        n = reads_mod.views_for(render.slug(e), reads)
        if n > PROTECT_ABOVE:
            print(f'  ..  {e["thinker"]:<10} {e["object"][:22]:<22} '
                  f"{n} reads - left alone")
            protected += 1
            continue
        try:
            essay, verdict, score, provider, on_topic, by = write_stage.write(
                thinker, e["object"], kind=e.get("kind"))
        except Exception as exc:                     # noqa: BLE001
            # A spent quota mid-run keeps everything already rewritten. Tomorrow picks
            # up where this stopped, because the backlog is derived from the gates
            # rather than from a marker this run has to remember to set.
            print(f'  !! {e["thinker"]}/{e["object"]}: {type(exc).__name__}: {exc}'[:120])
            break
        # RULE 1. The fallback wrote the original; letting it write the replacement
        # spends a call to produce the same genre again.
        if provider != write_stage.SCORER:
            print(f'  -- {e["thinker"]}/{e["object"]}: written by {provider}, not '
                  f"{write_stage.SCORER} - left alone, stopping for today")
            break
        # RULE 2. The replacement must clear the gates that rejected the original.
        new = dict(e, essay=essay, verdict=verdict, score=score)
        still = faults(new, thinker)
        if still or not essay:
            print(f'  xx  {e["thinker"]:<10} {e["object"][:22]:<22} '
                  f'rewrite still fails: {"; ".join(still) or "empty"} - kept the old one')
            refused += 1
            continue
        if score is None or not on_topic:
            print(f'  xx  {e["thinker"]:<10} {e["object"][:22]:<22} '
                  f"score {score!r}, on_topic {on_topic} - kept the old one")
            refused += 1
            continue
        print(f'  ->  {e["thinker"]:<10} {e["object"][:22]:<22} '
              f'{e.get("score")} -> {score}   {e.get("verdict","")!r} -> {verdict!r}')
        if not args.dry:
            e.update(essay=essay, verdict=verdict, score=score,
                     provider=provider, scored_by=by)
        done += 1

    left = len(backlog) - (0 if args.dry else done)
    print(f"\n{done} rewritten, {left} still queued"
          + (f", {protected} left alone as well-read" if protected else "")
          + (f", {refused} rewrites refused" if refused else ""))
    # Same alarm as rescore.py. A run that repairs nothing while a backlog exists is
    # silent by construction: the step exits 0 and the job goes green.
    if left and not done and os.environ.get("GITHUB_ACTIONS"):
        print(f"::warning::revoice rewrote nothing this run; {left} essays still "
              "queued. Expected on a day the free tier is spent. If this repeats "
              "for several days the drain has stopped working.")
    if args.dry or not done:
        return 0
    ESSAYS.write_text(json.dumps(entries, indent=2, ensure_ascii=False),
                      encoding="utf-8", newline="\n")
    render.build(entries, styles.load())
    print("archive written and pages re-rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
