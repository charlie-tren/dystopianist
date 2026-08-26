"""Produce one essay and add it to the archive.

    python run.py                  # today's pairing
    python run.py --dry            # generate and gate, write nothing
    python run.py --writer kafka   # a named writer instead of the rotation
    python run.py --until 2        # keep going until every writer has 2 essays

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


def pick(thinkers, objects, past, only=None):
    """Prefer the shortlisted pairings while any are left.

    Each object in the config names the two or three writers with a specific reason
    to have an opinion on it. Those go first, so the early essays are the strong
    matchups rather than whatever the shuffle produced; once they are spent it falls
    back to the whole roster, because a writer meeting something they have no claim
    on is half the point."""
    used = {(e["thinker"], e["object"]) for e in past}
    last = past[-1]["thinker"] if past else None
    ids = [only] if only else [x["id"] for x in thinkers]
    if only:
        last = None                    # a targeted backfill is not the daily rotation

    free = [(t, o["name"]) for t in ids for o in objects
            if (t, o["name"]) not in used and t != last]
    shortlisted = [(t, o["name"]) for t in ids for o in objects
                   if t in (o.get("writers") or []) and (t, o["name"]) not in used
                   and t != last]
    if not free:                       # every pair spent: allow repeats, still not twice running
        free = [(t, o["name"]) for t in ids for o in objects if t != last]
    return random.choice(shortlisted or free)


def main() -> int:
    _env.load()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--writer", help="writer id, instead of the daily rotation")
    ap.add_argument("--until", type=int, metavar="N",
                    help="backfill until every writer has N essays")
    args = ap.parse_args()

    thinkers = styles.load()
    objects = load("objects.yaml")["objects"]
    by_id = {t["id"]: t for t in thinkers}
    shots = {t["id"]: t["shot"] for t in thinkers}

    past = json.loads(ARCHIVE.read_text(encoding="utf-8")) if ARCHIVE.exists() else []

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
    thinker = by_id[tid]
    print(f"{thinker['name']} on {obj}")

    # Re-roll on a failed gate rather than publishing something that failed one.
    # Temperature climbs a little each time: the same prompt at the same heat
    # tends to reproduce the same mistake.
    essay, problems = "", ["not attempted"]
    verdict, score = "", None
    for i in range(ATTEMPTS):
        essay, verdict, score, provider, on_topic = write_stage.write(
            thinker, obj, temperature=0.9 + 0.05 * i)
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
    }
    past.append(entry)
    ARCHIVE.parent.mkdir(exist_ok=True)
    ARCHIVE.write_text(json.dumps(past, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    render.build(past, thinkers)
    print(f"wrote essay {len(past)} and rebuilt the site")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
