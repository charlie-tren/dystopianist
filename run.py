"""Produce one essay and add it to the archive.

    python run.py                  # today's pairing
    python run.py --dry            # generate and gate, write nothing
    python run.py --writer kafka   # a named writer instead of the rotation
    python run.py --until 2        # keep going until every writer has 2 essays
    python run.py --cover          # keep going until every subject has one

The pairing is the anti-repeat axis: never the same thinker-object pair twice, and
never the same thinker two days running. Shortlisted pairings - see pick() - go
first, so the strong matchups are not left to the shuffle.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import sys
from datetime import date, timezone, datetime
from pathlib import Path

import yaml

import _env
import critic
import llm
import styles
import render
import write as write_stage

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "data" / "essays.json"
ATTEMPTS = 3


def load(name):
    return yaml.safe_load(io.open(ROOT / "config" / name, encoding="utf-8"))


def died(thinker) -> int:
    """The year on the right of `dates:`. Every writer here died AD and none of the
    ranges carry a BC, so the plain int is enough."""
    return int(str(thinker.get("dates", "0-0")).split("-")[-1])


def eligible(thinker, obj) -> bool:
    """A writer may only be set on something that postdates them.

    Only dated objects are constrained. An alarm clock has no year and everyone is
    eligible; a film does, and the whole premise of the site collapses the moment
    Didion is asked what she made of a film she reviewed. The check lives HERE and
    not only in the shortlists because the fallback below draws from the whole
    roster, which is precisely where an ineligible pairing would appear."""
    year = obj.get("year")
    return year is None or died(thinker) < year


def pick(thinkers, objects, past, only=None):
    """Cover every subject first, then prefer the shortlisted pairings.

    Two preferences, in order. An object nobody has written about yet outranks
    everything: the site promises a take on each subject, and a subject sitting on
    nought reads as an empty shelf rather than as a queue. The five films added on
    26/08/2026 sat at nought for two days because the pairing only ever balanced
    WRITERS, so a new subject could wait out the whole rotation.

    Within each of those, the shortlisted writers go first - the two or three the
    config names as having a specific reason to have an opinion - so the early
    essays are the strong matchups rather than whatever the shuffle produced. Once
    the shortlists are spent it falls back to the whole roster, because a writer
    meeting something they have no claim on is half the point.
    """
    used = {(e["thinker"], e["object"]) for e in past}
    covered = {e["object"] for e in past}
    last = past[-1]["thinker"] if past else None
    by_id = {t["id"]: t for t in thinkers}
    ids = [only] if only else [x["id"] for x in thinkers]
    if only:
        last = None                    # a targeted backfill is not the daily rotation

    def ok(t, o):
        return t != last and t in by_id and eligible(by_id[t], o)

    def pairs(pool, shortlisted_only):
        return [(t, o["name"]) for t in ids for o in pool
                if (t, o["name"]) not in used and ok(t, o)
                and (not shortlisted_only or t in (o.get("writers") or []))]

    new = [o for o in objects if o["name"] not in covered]
    for pool in (pairs(new, True), pairs(new, False),
                 pairs(objects, True), pairs(objects, False)):
        if pool:
            return random.choice(pool)
    # Every pair is spent: allow a repeat, still never the same writer twice running.
    return random.choice([(t, o["name"]) for t in ids for o in objects if ok(t, o)])


def main() -> int:
    _env.load()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--writer", help="writer id, instead of the daily rotation")
    ap.add_argument("--until", type=int, metavar="N",
                    help="backfill until every writer has N essays")
    ap.add_argument("--cover", action="store_true",
                    help="backfill until every subject has at least one essay")
    args = ap.parse_args()

    thinkers = styles.load()
    objects = load("objects.yaml")["objects"]
    by_id = {t["id"]: t for t in thinkers}
    shots = {t["id"]: t["shot"] for t in thinkers}

    past = json.loads(ARCHIVE.read_text(encoding="utf-8")) if ARCHIVE.exists() else []

    if args.cover:
        # Subject coverage, run BEFORE the writer top-up. pick() already prefers an
        # uncovered subject, so this is only the difference between covering them
        # over five nights and covering them tonight - which matters when a batch of
        # subjects is added at once and the page shows five noughts until it drains.
        if args.dry:
            print("--cover writes; it cannot be combined with --dry", file=sys.stderr)
            return 2

        def uncovered():
            done = {e["object"] for e in past}
            return [o["name"] for o in objects if o["name"] not in done]

        while uncovered():
            left = uncovered()
            print(f"\n--- covering {left[0]} ({len(left)} subject(s) at nought) ---")
            try:
                failed = one(None, thinkers, objects, by_id, shots, past, args.dry)
            except llm.NoProvider as exc:
                print(f"\nout of free quota with {len(left)} subject(s) still at "
                      f"nought: {exc}", file=sys.stderr)
                return 3
            if failed:
                print(f"giving up on {left[0]}", file=sys.stderr)
                return 1
            if uncovered() == left:
                # pick() chose a covered subject anyway - eligibility can leave a
                # subject with no writer the rotation will give it. Loud, and a stop
                # rather than the same choice forever.
                print(f"::warning::{left[0]} is still at nought after a write - "
                      f"stopping the coverage pass", file=sys.stderr)
                break

    if args.until:
        # Backfill: the writers page shows a nought beside anyone in the rotation
        # who has not been drawn yet, so a new writer looks broken until they have
        # a couple. Each round writes and re-renders, so an interrupted run keeps
        # everything it managed.
        if args.dry:
            print("--until writes; it cannot be combined with --dry", file=sys.stderr)
            return 2

        def short():
            n = {t["id"]: 0 for t in thinkers}
            for e in past:
                if e["thinker"] in n:
                    n[e["thinker"]] += 1
            return sorted(k for k, v in n.items() if v < args.until)

        while short():
            tid = short()[0]
            print(f"\n--- {tid} ({len(short())} writer(s) still short of {args.until}) ---")
            try:
                failed = one(tid, thinkers, objects, by_id, shots, past, args.dry)
            except llm.NoProvider as exc:
                # Both free tiers are day-limited, so a long backfill can simply run
                # out. Everything written so far is already on disk and rendered;
                # re-running the same command tomorrow picks up where it stopped.
                print(f"\nout of free quota after {len(past)} essay(s): {exc}",
                      file=sys.stderr)
                print(f"{len(short())} writer(s) still short - re-run "
                      f"'python run.py --until {args.until}' once the quota resets",
                      file=sys.stderr)
                return 3
            if failed:
                print(f"giving up on {tid}", file=sys.stderr)
                return 1
        # Fall through to today's essay. Without this the daily job would go silent
        # the moment the backfill finished: --until would find nobody short, print a
        # cheerful line and write nothing, every day, forever.
        print(f"\nevery writer has at least {args.until} - writing today's essay")

    try:
        return one(args.writer, thinkers, objects, by_id, shots, past, args.dry)
    except llm.NoProvider as exc:
        # Same treatment as the backfill: an exhausted free tier is an expected
        # daily condition, not a crash worth a traceback.
        print(f"out of free quota: {exc}", file=sys.stderr)
        return 3


def one(only, thinkers, objects, by_id, shots, past, dry) -> int:
    tid, obj = pick(thinkers, objects, past, only)
    kind = next((o.get("kind") for o in objects if o["name"] == obj), None)
    thinker = by_id[tid]
    print(f"{thinker['name']} on {obj}")

    # Re-roll on a failed gate rather than publishing something that failed one.
    # Temperature climbs a little each time: the same prompt at the same heat
    # tends to reproduce the same mistake.
    essay, problems = "", ["not attempted"]
    verdict, score = "", None
    for i in range(ATTEMPTS):
        essay, verdict, score, provider, on_topic, scored_by = write_stage.write(
            thinker, obj, temperature=0.9 + 0.05 * i, kind=kind)
        problems = critic.check(essay, thinker, shots, verdict, score, on_topic)
        status = "ok" if not problems else "; ".join(problems)
        print(f"  attempt {i + 1}: {len(essay.split())} words via {provider} "
              f"- {verdict} {score} - {status}")
        if not problems:
            break
    if problems:
        print("FAILED: no attempt cleared the gates", file=sys.stderr)
        return 1

    if dry:
        print("\n" + essay + "\n(dry run, nothing written)")
        return 0

    entry = {
        "date": date.today().isoformat(),
        "thinker": tid,
        "name": thinker["name"],
        "dates": thinker["dates"],
        "object": obj,
        "verdict": verdict,
        "score": score,
        "essay": essay,
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "provider": provider,
        # Which model READ it. See write.SCORER: a score only means anything against
        # the other scores on the page, so one written by the fallback is repaired by
        # tools/rescore.py rather than left on a different scale from its neighbours.
        "scored_by": scored_by,
    }
    past.append(entry)
    ARCHIVE.parent.mkdir(exist_ok=True)
    ARCHIVE.write_text(json.dumps(past, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    render.build(past, thinkers)
    print(f"wrote essay {len(past)} and rebuilt the site")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
