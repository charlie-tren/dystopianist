"""Produce one essay and add it to the archive.

    python run.py            # today's pairing
    python run.py --dry      # generate and gate, write nothing

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
import render
import write as write_stage

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "data" / "essays.json"
ATTEMPTS = 3


def load(name):
    return yaml.safe_load(io.open(ROOT / "config" / name, encoding="utf-8"))


def pick(thinkers, objects, past):
    used = {(e["thinker"], e["object"]) for e in past}
    last = past[-1]["thinker"] if past else None
    pool = [(t, o) for t in (x["id"] for x in thinkers) for o in objects
            if (t, o) not in used and t != last]
    if not pool:                       # every pair spent: allow repeats, still not twice running
        pool = [(t, o) for t in (x["id"] for x in thinkers) for o in objects if t != last]
    return random.choice(pool)


def main() -> int:
    _env.load()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    thinkers = load("thinkers.yaml")["thinkers"]
    objects = load("objects.yaml")["objects"]
    by_id = {t["id"]: t for t in thinkers}
    shots = {t["id"]: t["shot"] for t in thinkers}

    past = json.loads(ARCHIVE.read_text(encoding="utf-8")) if ARCHIVE.exists() else []
    tid, obj = pick(thinkers, objects, past)
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

    if args.dry:
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
