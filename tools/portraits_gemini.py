"""Draw a missing portrait with Gemini instead of Cloudflare, matching the existing hand.

    python tools/portraits_gemini.py --only=adams --out=docs/faces/_gem --tries=3

DOES NOT RUN ON THE FREE TIER. Measured 28/08/2026: the key lists six image models and
every one of them answers 429, with a retryDelay around thirty seconds that does not
clear - two honoured 57-second waits changed nothing - while the TEXT model on the same
key answers 200 in the same minute. So the refusal is not congestion and not the daily
text quota; image generation is simply not included. The one thing that would change it
is billing enabled on the Google project, which is why this is kept rather than deleted.

Why it was written: Cloudflare's free image allowance is a rolling window from the
spend, not a calendar day, so a heavy evening blocks the next one and a new writer can
wait days for a face. Gemini looked like the second provider.

The interesting difference is not the quota. **Flux Schnell takes no seed and no
reference image**, so eighteen portraits drawn with it are eighteen unrelated
commissions that happen to share a style string. Gemini takes REFERENCE IMAGES, so this
sends three of the existing portraits and asks for the same hand - which is a stronger
guarantee of a consistent set than the Cloudflare path could ever offer.

It reuses LOOK and STYLE from tools/portraits.py rather than restating them: two
descriptions of the same writer that drift apart is exactly the bug worth avoiding.
Output goes through the same greyscale, inset crop and 512px resize, so a Gemini face
and a Flux face are the same kind of file.
"""
from __future__ import annotations

import base64
import io as _io
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _env  # noqa: E402
import styles  # noqa: E402
from portraits import LOOK, STYLE, crop  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "faces"
MODEL = "gemini-3.1-flash-image"

# Three references, chosen for range rather than for being the best: an old man with a
# huge beard, a young clean-shaven man, a woman. A model shown three similar faces
# copies the face; shown three different ones it copies the HAND, which is the point.
REFS = ["whitman", "kafka", "didion"]


def retry_delay(resp):
    """Seconds Google asks us to wait, or None when it offers no retry at all."""
    try:
        for d in resp.json()["error"].get("details", []):
            if str(d.get("@type", "")).endswith("RetryInfo"):
                return int(float(str(d["retryDelay"]).rstrip("s")))
    except Exception:                                  # noqa: BLE001
        pass
    return None


def draw(key: str, look: str, model: str) -> bytes:
    parts = []
    for r in REFS:
        p = OUT / f"{r}.jpg"
        if p.exists():
            parts.append({"inline_data": {"mime_type": "image/jpeg",
                                          "data": base64.b64encode(p.read_bytes()).decode()}})
    parts.append({"text":
        "The images above are from a single set of hand-drawn ink caricature portraits, "
        "all by the same illustrator. Draw ONE more portrait for the same set, matching "
        "their line weight, cross-hatching, framing and tone exactly. It must look like "
        "the same hand drew it on the same afternoon.\n\n"
        f"The subject: {look}\n\n"
        f"Style: {STYLE}\n\n"
        "Head and shoulders, centred, plain white background, no border, and no text, "
        "signature or lettering anywhere in the image."})

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
           ":generateContent")
    # Gemini's free tier meters per MINUTE as well as per day, and the two are easy to
    # confuse: both come back 429 with the same "exceeded your current quota" message.
    # The difference is in the RetryInfo - a per-minute refusal carries a retryDelay of
    # about twenty seconds, a spent day does not. So honour the delay it names rather
    # than reading the message, and give up only when it stops offering one.
    for attempt in range(4):
        r = requests.post(url, headers={"x-goog-api-key": key},
                          json={"contents": [{"parts": parts}]}, timeout=180)
        if r.status_code != 429:
            break
        wait = retry_delay(r)
        if wait is None or attempt == 3:
            break
        print(f"    per-minute limit, waiting {wait}s")
        time.sleep(wait + 2)
    r.raise_for_status()
    for part in r.json()["candidates"][0]["content"]["parts"]:
        blob = part.get("inline_data") or part.get("inlineData")
        if blob:
            return base64.b64decode(blob["data"])
    raise RuntimeError("no image in the response: "
                       + str(r.json())[:200])


def arg(name, default=""):
    for a in sys.argv:
        if a.startswith(f"--{name}="):
            return a.split("=", 1)[1]
    return default


def main() -> int:
    _env.load()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY not set", file=sys.stderr)
        return 1
    only = {x.strip() for x in arg("only").split(",") if x.strip()}
    tries = max(1, int(arg("tries", "1")))
    model = arg("model", MODEL)
    dest_dir = ROOT / arg("out") if arg("out") else OUT
    dest_dir.mkdir(parents=True, exist_ok=True)

    drawn = 0
    for t in styles.load():
        tid = t["id"]
        if only and tid not in only:
            continue
        if not only and (OUT / f"{tid}.jpg").exists():
            print(f"{tid:10} already drawn")
            continue
        look = LOOK.get(tid)
        if not look:
            print(f"{tid:10} no LOOK entry", file=sys.stderr)
            continue
        for n in range(tries):
            target = dest_dir / (f"{tid}.jpg" if tries == 1 else f"{tid}-{n + 1}.jpg")
            try:
                raw = draw(key, look, model)
            except Exception as exc:                   # noqa: BLE001
                print(f"{tid:10} FAILED {type(exc).__name__}: {str(exc)[:140]}")
                continue
            from PIL import Image
            im = Image.open(_io.BytesIO(raw)).convert("L").convert("RGB")
            im = crop(im).resize((512, 512), Image.LANCZOS)
            im.save(target, "JPEG", quality=82, optimize=True)
            drawn += 1
            print(f"{target.name:16} {target.stat().st_size // 1024}KB via {model}")
    print(f"\n{drawn} image(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
