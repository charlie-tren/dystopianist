"""Generate a cartoon portrait per writer, free, on Cloudflare Workers AI.

    python tools/portraits.py                     # only writers without a portrait
    python tools/portraits.py --force             # redraw everything
    python tools/portraits.py --only orwell,kafka # redraw just these
    python tools/portraits.py --model=sdxl        # a different image model

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

# Flux Schnell is a distilled 4-8 step model: fast and free, but the line quality is
# the weakest part of the set. The alternatives are here so the choice can be
# COMPARED rather than assumed - run --model sdxl and put the two side by side.
MODELS = {
    "flux":       "@cf/black-forest-labs/flux-1-schnell",
    "sdxl":       "@cf/stabilityai/stable-diffusion-xl-base-1.0",
    "lightning":  "@cf/bytedance/stable-diffusion-xl-lightning",
    "dreamshaper": "@cf/lykon/dreamshaper-8-lcm",
}
MODEL = MODELS["flux"]
OUT = Path(__file__).resolve().parent.parent / "docs" / "faces"

# One line each, describing the PERSON not the style - the style is the same for
# all eight so the set reads as one hand.
LOOK = {
    "wallace":  "a man in his thirties with long hair under a white bandana, round glasses, unshaven",
    "orwell":   "a gaunt Englishman with a thin moustache, tweed jacket, tired eyes",
    "twain":    "an older man with a full white walrus moustache and wild white hair, white suit",
    "wilde":    "a heavyset Victorian dandy with a soft jowly face, mid-length wavy hair parted in the centre and falling to the collar, heavy-lidded eyes, fur-collared overcoat",
    "aurelius": "a bearded Roman emperor in a plain toga, curly hair and beard, weary",
    "kafka":    "a thin young man in a dark suit and stiff collar, black hair swept straight back, a narrow face and large dark intense eyes",
    "thompson": "a bald man in aviator sunglasses with a cigarette holder clenched in his teeth, bucket hat",
    "nietzsche": "a stern 19th-century German man with SHORT dark hair combed flat, a very heavy drooping moustache covering the mouth, deep-set eyes under heavy brows, buttoned dark coat",
    "montaigne": "a balding 16th-century Frenchman with a pointed beard and a wide starched ruff collar",
    "ephron":   "a dark-haired American woman in her sixties, short practical haircut, amused sceptical expression, plain shirt",
    "didion":   "a very slight woman in her sixties, dark sunglasses, straight shoulder-length hair, cigarette, cool unsmiling expression",
}

# Black and white only. The first set carried an ochre accent and Flux kept turning it
# into a stray blob beside the face; monochrome removes the blob and the decision.
STYLE = ("hand-drawn ink caricature portrait, black and white only, monochrome, no colour, "
         "loose confident line work, cross-hatching, white paper, head and shoulders, "
         "plain empty background, editorial illustration, clean empty margins, unsigned, "
         "no text anywhere, no lettering, no words, no signature, no watermark, no stray marks")


def draw(acct: str, tok: str, prompt: str, model: str, steps: int) -> bytes:
    """Flux answers with base64 inside JSON; the Stable Diffusion endpoints answer
    with raw PNG bytes. Handle both rather than assuming the one we started with."""
    body = {"prompt": prompt, "steps": steps}
    if "flux" not in model:
        # Flux Schnell 400s on ANY field it does not know - it takes prompt and steps
        # and nothing else, no negative prompt and no seed. Verified against the API,
        # not assumed. The Stable Diffusion endpoints take both, and a SHARED seed is
        # what would make the set read as one hand rather than eleven unrelated
        # commissions - which is a reason to prefer them over Flux for this job.
        body["negative_prompt"] = ("text, lettering, words, signature, watermark, "
                                   "colour, blurry, smudged, low detail")
        body["seed"] = SEED
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}",
                      headers={"Authorization": f"Bearer {tok}"}, json=body, timeout=180)
    r.raise_for_status()
    if "image" in r.headers.get("content-type", ""):
        return r.content
    d = r.json()
    if not d.get("success"):
        raise RuntimeError(str(d.get("errors"))[:200])
    img = d["result"].get("image")
    if not img:
        raise RuntimeError(f"no image in response: {list(d['result'])}")
    return base64.b64decode(img)


# Flux signs these however firmly the prompt says not to - a scrawled fake artist
# name, always within a few percent of a corner. Trimming the margin removes it and
# tightens the framing, which the head-and-shoulders composition can spare.
INSET = 0.09

# One seed for the whole set, so the style is a constant and only the face varies.
# Ignored by Flux, which does not accept one.
SEED = 774411


def crop(im):
    w, h = im.size
    return im.crop((int(w * INSET), int(h * INSET),
                    int(w * (1 - INSET)), int(h * (1 - INSET))))


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
    which = next((a.split("=", 1)[-1] for a in sys.argv if a.startswith("--model=")), "flux")
    if which not in MODELS:
        print(f"--model must be one of {', '.join(MODELS)}", file=sys.stderr)
        return 1
    model = MODELS[which]
    steps = 8 if which == "flux" else 20
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
            raw = draw(acct, tok, prompt, model, steps)
        except Exception as exc:                       # noqa: BLE001
            print(f"{t['id']:10} FAILED {type(exc).__name__}: {str(exc)[:110]}")
            continue
        from PIL import Image
        im = Image.open(_io.BytesIO(raw)).convert("L").convert("RGB")
        im = crop(im).resize((512, 512), Image.LANCZOS)
        im.save(dest, "JPEG", quality=82, optimize=True)
        print(f"{t['id']:10} {dest.stat().st_size // 1024}KB via {which}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
