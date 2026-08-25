"""Generate a cartoon portrait per writer, free, on Cloudflare Workers AI.

    python tools/portraits.py                     # only writers without a portrait
    python tools/portraits.py --force             # redraw everything
    python tools/portraits.py --only orwell,kafka # redraw just these

Deliberately CARTOON, not photoreal. These are real people and the site already
says the essays are pastiche; a photorealistic fake portrait would undercut that,
while a drawing reads the way a newspaper caricature does - obviously an
impression of someone rather than a picture of them.

Flux Schnell is the free-tier model The Aftertimes already uses for its
illustrations, so this costs nothing new.
"""
from __future__ import annotations

import base64
import io as _io
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _env  # noqa: E402
import styles  # noqa: E402

MODEL = "@cf/black-forest-labs/flux-1-schnell"
OUT = Path(__file__).resolve().parent.parent / "docs" / "faces"

# One line each, describing the PERSON not the style - the style is the same for
# all eight so the set reads as one hand.
LOOK = {
    "wallace":  "a man in his thirties with long hair under a white bandana, round glasses, unshaven",
    "orwell":   "a gaunt Englishman with a thin moustache, tweed jacket, tired eyes",
    "twain":    "an older man with a full white walrus moustache and wild white hair, white suit",
    "wilde":    "a heavyset young Victorian dandy with a centre parting, fur-collared coat, green carnation",
    "aurelius": "a bearded Roman emperor in a plain toga, curly hair and beard, weary",
    "kafka":    "a thin young man in a dark suit and stiff collar, enormous dark eyes, ears sticking out",
    "thompson": "a bald man in aviator sunglasses with a cigarette holder clenched in his teeth, bucket hat",
    "didion":   "a very slight woman in her sixties, dark sunglasses, straight shoulder-length hair, cigarette, cool unsmiling expression",
}

STYLE = ("hand-drawn ink caricature portrait, loose confident line work, cross-hatching, "
         "warm cream paper, single muted ochre accent, head and shoulders, plain background, "
         "editorial illustration, clean empty margins, "
         "no text anywhere, no lettering, no words, no signature, no watermark")


def draw(acct: str, tok: str, prompt: str) -> bytes:
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{MODEL}",
                      headers={"Authorization": f"Bearer {tok}"},
                      json={"prompt": prompt, "steps": 8}, timeout=180)
    r.raise_for_status()
    d = r.json()
    if not d.get("success"):
        raise RuntimeError(str(d.get("errors"))[:200])
    img = d["result"].get("image")
    if not img:
        raise RuntimeError(f"no image in response: {list(d['result'])}")
    return base64.b64decode(img)


def main() -> int:
    _env.load()
    acct, tok = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not (acct and tok):
        print("CF_ACCOUNT_ID / CF_API_TOKEN not set", file=sys.stderr)
        return 1
    force = "--force" in sys.argv
    only = next((a.split("=", 1)[-1] for a in sys.argv if a.startswith("--only")), "")
    if only == "--only":                               # "--only x" rather than "--only=x"
        only = sys.argv[sys.argv.index("--only") + 1]
    wanted = {x.strip() for x in only.split(",") if x.strip()}
    OUT.mkdir(parents=True, exist_ok=True)
    for t in styles.load():
        if wanted and t["id"] not in wanted:
            continue
        dest = OUT / f"{t['id']}.jpg"
        if dest.exists() and not (force or wanted):
            print(f"{t['id']:10} already drawn")
            continue
        prompt = f"{LOOK[t['id']]}. {STYLE}"
        try:
            raw = draw(acct, tok, prompt)
        except Exception as exc:                       # noqa: BLE001
            print(f"{t['id']:10} FAILED {type(exc).__name__}: {str(exc)[:110]}")
            continue
        from PIL import Image
        im = Image.open(_io.BytesIO(raw)).convert("RGB")
        im = im.resize((360, 360), Image.LANCZOS)
        im.save(dest, "JPEG", quality=82, optimize=True)
        print(f"{t['id']:10} {dest.stat().st_size // 1024}KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
