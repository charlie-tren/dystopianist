"""Generate a cartoon portrait per writer, free, on Cloudflare Workers AI.

    python tools/portraits.py                     # only writers without a portrait
    python tools/portraits.py --force             # redraw everything
    python tools/portraits.py --only orwell,kafka # redraw just these
    python tools/portraits.py --model=sdxl        # a different image model
    python tools/portraits.py --force --out docs/faces/_preview --model=lightning
    python tools/portraits.py --only austen --out docs/faces/_preview --tries 4

The last form is how a change to the model or the STYLE string gets JUDGED before it
lands: it draws into a throwaway directory, so the live set is untouched and the two
can be put side by side. Replacing eighteen faces in place and then deciding is not
reversible in any useful sense - the previous draw is gone even if the file is not.

REVIEWING the set means building a contact sheet and reading each face AGAINST its own
LOOK line below - not glancing at the folder. The faults are specific and quiet: a
signature inked onto a shoulder, hair the line explicitly forbids, a moustache curling
the way the line says it must not. Two sweeps missed a fake signature on Whitman
because nobody compared the drawing to the description that asked for it.

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
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "faces"

# One line each, describing the PERSON not the style. Three of these carry anti-
# glamour wording ("a plain ordinary face", "scratchy pen lines"): asked for a young
# woman with a smooth face the model leaves the editorial-ink style entirely and
# returns a doe-eyed vector illustration, which is what Austen and Dickinson were
# until 26/08/2026. The style string is shared by all eighteen, so the correction
# has to sit on the faces that need it.
#
# Some of it Flux will not do however it is worded. Three rounds on 28/08/2026 could
# not get a flat uncurled moustache onto Proust or a bare upper lip onto Thoreau -
# the caricature prior wins, and every candidate came back a handlebar. Rewriting the
# line again is not the lever; drawing three or four and picking is. Wording that has
# been tried and lost is left in place rather than escalated.
# EVERY id in styles/ must appear here. A writer added to styles/ and forgotten here
# raises KeyError and takes the whole workflow with it - on 26/08/2026 that killed the
# portraits step, which skipped the Commit step, which threw away a completed reverdict
# pass in the same run. main() now reports the missing ones and draws the rest.
LOOK = {
    "wallace":  "a man in his thirties with long hair under a white bandana, round glasses, unshaven",
    "orwell":   "a gaunt Englishman with a thin moustache, tweed jacket, tired eyes",
    "twain":    "an older man with a full white walrus moustache and wild white hair, white suit",
    "wilde":    "a heavyset Victorian dandy with a soft jowly face, mid-length wavy hair parted in the centre and falling to the collar, heavy-lidded eyes, fur-collared overcoat",
    "aurelius": "a bearded Roman emperor in a plain toga, curly hair and beard, weary",
    "kafka":    "a thin young man in a dark suit and stiff collar, black hair swept straight back, a narrow face and large dark intense eyes",
    "thompson": "a bald man in aviator sunglasses with a cigarette holder clenched in his teeth, bucket hat",
    "nietzsche": "a stern 19th-century German man whose hair is cropped close and plastered flat to the skull with no volume and no waves, a heavy walrus moustache that hangs straight DOWN over the mouth with its ends drooping below the corners of the lips, never waxed, never curled, never turned up at the ends, the chin and cheeks clean-shaven so there is a moustache and no beard at all, deep-set eyes under heavy brows, buttoned dark coat",
    "montaigne": "a balding 16th-century Frenchman with a pointed beard and a wide starched ruff collar",
    "ephron":   "a dark-haired American woman in her sixties, short practical haircut, amused sceptical expression, plain shirt",
    "didion":   "a very slight woman in her sixties, dark sunglasses, straight shoulder-length hair, cigarette, cool unsmiling expression",
    "proust":   "a pale young Frenchman of the 1900s with a modest dark moustache sitting flat and low on the upper lip, no wider than the mouth itself, ends hanging slightly down, absolutely not a large waxed handlebar and not curled upward, very large dark eyes with dark rings beneath them, thick black hair, high stiff collar and cravat, an invalid's delicacy",
    "whitman":  "an old American with a huge untrimmed white beard spreading over his chest, a broad soft hat worn at an angle, open shirt collar, no tie, weathered kindly face",
    "austen":   "a young Englishwoman of about 1800 wearing a frilled white day cap tied under the chin with dark curls escaping at the temples, a high-waisted Regency dress, small knowing half-smile, a plain ordinary long-nosed face rather than a beautiful one, drawn in scratchy pen lines with heavy visible hatching over the face, never a smooth doe-eyed illustration",
    "woolf":    "an Englishwoman with a long narrow face and heavy-lidded eyes, dark hair pinned loosely back, a slightly haunted inward expression, plain high-necked blouse",
    "dickinson": "a young woman of the 1850s with hair parted severely in the centre and drawn back flat, a plain dark high-necked dress with a narrow white collar, very still direct unblinking gaze, a gaunt severe unsmiling face with hollow cheeks and a long jaw, drawn in scratchy scratchboard pen lines with heavy visible cross-hatching over the whole face, deliberately unglamorous, never a smooth clean-lined or doe-eyed illustration",
    "dickens":  "a Victorian gentleman with long wavy hair to the collar and a full straggling beard, deep-set lively eyes, velvet-collared coat and watch chain",
    "adams":    "a tall Englishman in his forties with a large forehead and receding fine brown hair, a long face, a gentle amused expression, a slightly rumpled shirt and no tie",
    "franklin": "a stout 18th-century American with a high domed bald crown and long straight hair falling to the shoulders, small oval spectacles low on the nose, a plain heavy coat, a shrewd amused expression",
    "tolstoy":  "an old Russian with an enormous untrimmed white beard reaching his chest, a bald crown with white hair at the sides, fierce deep-set eyes under heavy white brows, a loose belted peasant smock",
    "child":    "a very tall American woman in her fifties with short wavy hair, a long face and a wide delighted open-mouthed smile, a plain blouse with a kitchen apron over it",
    "bourdain": "a tall lean American man in his late fifties with a deeply lined weathered face, short spiky silver-grey hair, a long nose and a wry sceptical half-smile, an open-collared shirt with the sleeves pushed up",
    "thoreau":  "a plain-featured 19th-century New Englander wearing a chin curtain: the beard grows in a narrow fringe under the jaw and chin only, while the upper lip is shaved bare with no moustache of any kind and the cheeks are shaved bare, unruly hair, a long nose, homespun jacket",
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
    missing: list[str] = []
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
    out = next((a.split("=", 1)[-1] for a in sys.argv if a.startswith("--out=")), "")
    if not out and "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    dest_dir = (ROOT / out) if out else OUT
    dest_dir.mkdir(parents=True, exist_ok=True)
    tries = next((a.split("=", 1)[-1] for a in sys.argv if a.startswith("--tries=")), "")
    if not tries and "--tries" in sys.argv:
        tries = sys.argv[sys.argv.index("--tries") + 1]
    # Flux takes no seed, so every call is a fresh roll and a bad face is not a bad
    # prompt - it is one bad roll. Drawing four and picking is the difference between
    # editing the description and editing the outcome.
    tries = max(1, int(tries or 1))
    for t in styles.load():
        if wanted and t["id"] not in wanted:
            continue
        dest = dest_dir / f"{t['id']}.jpg"
        if dest.exists() and not (force or wanted):
            print(f"{t['id']:10} already drawn")
            continue
        look = LOOK.get(t["id"])
        if not look:
            missing.append(t["id"])
            continue
        prompt = f"{look}. {STYLE}"
        for n in range(tries):
            target = dest if tries == 1 else dest.with_name(f"{t['id']}-{n + 1}.jpg")
            try:
                raw = draw(acct, tok, prompt, model, steps)
            except Exception as exc:                   # noqa: BLE001
                print(f"{t['id']:10} FAILED {type(exc).__name__}: {str(exc)[:110]}")
                continue
            from PIL import Image
            im = Image.open(_io.BytesIO(raw)).convert("L").convert("RGB")
            im = crop(im).resize((512, 512), Image.LANCZOS)
            im.save(target, "JPEG", quality=82, optimize=True)
            print(f"{target.name:16} {target.stat().st_size // 1024}KB via {which}")
    if missing:
        # Loud, but not fatal. Everything drawable has been drawn and saved by now,
        # and taking the run down here would skip the commit that keeps it.
        print("")
        print("::warning::no LOOK entry, not drawn: "
              + ", ".join(sorted(missing)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
