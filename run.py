"""Produce one essay and add it to the archive.

    python run.py                  # today's pairing
    python run.py --dry            # generate and gate, write nothing
    python run.py --writer kafka   # a named writer instead of the rotation
    python run.py --until 2        # keep going until every writer has 2 essays

The pairing is the anti-repeat axis: never the same thinker-object pair twice, and
never the same thinker two days running. With 8 x 40 pairs that lasts most of a
year before it has to reach for a used pair.
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
import styles
import render
import write as write_stage

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "data" / "essays.json"
ATTEMPTS = 3


def load(name):
    return yaml.safe_load(io.open(ROOT / "config" / name, encoding="utf-8"))


def pick(thinkers, objects, past, only=None):
    used = {(e["thinker"], e["object"]) for e in past}
    last = past[-1]["thinker"] if past else None
    ids = [only] if only else [x["id"] for x in thinkers]
    if only:
        last = None                    # a targeted backfill is not the daily rotation
    pool = [(t, o) for t in ids for o in objects
            if (t, o) not in used and t != last]
    if not pool:                       # every pair spent: allow repeats, still not twice running
        pool = [(t, o) for t in ids for o in objects if t != last]
    return random.choice(pool)


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
            if one(tid, thinkers, objects, by_id, shots, past, args.dry):
                print(f"giving up on {tid}", file=sys.stderr)
                return 1
        print(f"\nevery writer has at least {args.until}")
        return 0

    return one(args.writer, thinkers, objects, by_id, shots, past, args.dry)


def one(only, thinkers, objects, by_id, shots, past, dry) -> int:
    tid, obj = pick(thinkers, objects, past, only)
    thinker = by_id[tid]
    print(f"{thinker['name']} on {obj}")

    # Re-roll on a failed gate rather than publishing something that failed one.
    # Temperature climbs a little each time: the same prompt at the same heat
    # tends to reproduce the same mistake.
    essay, problems = "", ["not attempted"]
    for i in range(ATTEMPTS):
        essay, provider = write_stage.write(thinker, obj, temperature=0.9 + 0.05 * i)
        problems = critic.check(essay, thinker, shots)
        status = "ok" if not problems else "; ".join(problems)
        print(f"  attempt {i + 1}: {len(essay.split())} words via {provider} - {status}")
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
