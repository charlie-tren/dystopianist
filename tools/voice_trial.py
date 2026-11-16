"""Write N fresh essays per writer and print how far apart their voices sit.

Run this BEFORE queueing a back catalogue for rewrite after a styles change. On
12/11/2026 a 3-essay trial put nietzsche/wilde at 0.80 and the 24 rewrites that
followed landed at 0.21: three essays is a lucky draw, not a measurement.

    python tools/voice_trial.py nietzsche wilde --n 10
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import styles  # noqa: E402
import voice  # noqa: E402
import write as write_stage  # noqa: E402

OBJECTS = ["airport lounges", "self-checkout machines", "LinkedIn", "audiobooks", "emojis",
           "Wikipedia", "step counters", "influencers", "airport security", "umbrellas",
           "group chats", "standing desks"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("writers", nargs="+")
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args()
    roster = {t["id"]: t for t in styles.load()}
    out = {w: [] for w in args.writers}
    for w in args.writers:
        for obj in OBJECTS[:args.n]:
            try:
                essay, _, _, provider, _, _ = write_stage.write(roster[w], obj)
            except Exception as exc:  # noqa: BLE001
                print(f"  !! {w}/{obj}: {type(exc).__name__}: {exc}"[:120])
                continue
            out[w].append({"object": obj, "provider": provider, "essay": essay})
            print(f"  {w:<10} {obj:<24} {provider}")
    (ROOT / "voice_trial.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    texts = {w: " ".join(e["essay"] for e in v) for w, v in out.items() if v}
    for w, t in texts.items():
        fp = voice.fingerprint(t)
        print(f"{w:<10} n={len(out[w])} " +
              " ".join(f"{k}={fp[k] / voice.SCALE[k]:.2f}" for k in voice.SCALE))
    if len(texts) >= 2:
        worst, pair = voice.divergence(texts)
        print(f"closest {pair[0]}/{pair[1]} {worst:.3f} (floor 0.45)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
