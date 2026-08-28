"""Build docs/og.png - the card WhatsApp, Slack and X show when the site is shared.

    python tools/make_og.py

Until 28/08/2026 the pages carried og:title and og:description and NO og:image, so a
link pasted into WhatsApp arrived as a bare line of text. The tags that were there
promised a card and never supplied one.

1200x630 at 2x, the size Slack and LinkedIn expect. Two constraints beyond looking
right:

- **Absolute URL.** WhatsApp will not resolve a relative og:image. This is the single
  most common reason a card that works in a local preview shows nothing in a chat.
- **Small file.** WhatsApp is the strictest of the lot on thumbnail size. Nine line
  drawings are where the bytes go: at 2400x1260 this card is 379KB even quantised to
  64 colours, against Shortfall's 93KB for a card of flat colour and big type. So it
  ships at 1200x630, which is the spec size anyway, rendered at 2x and downsampled -
  sharper than drawing at 1x for the same pixels. 128 colours lands it near 115KB.
  The check at the end FAILS the build rather than shipping a card that will silently
  not render, and it has already caught one.

The portraits ARE the site, so they are the card: nine faces, the mark, the lede.
"""
from __future__ import annotations

import base64
import io as _io
import pathlib
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "og.png"

# Chosen for range rather than for being the best drawings - a card of nine similar
# faces reads as a pattern, nine different ones read as a cast.
FACES = ["whitman", "kafka", "didion", "franklin", "child",
         "nietzsche", "austen", "thompson", "tolstoy"]

# WhatsApp's limit is not documented and moves; 300KB is the figure that has held.
MAX_KB = 300


def html() -> str:
    # Embedded as data URIs, not file:// paths. set_content() gives the page no base
    # URL and no file access, so a file:// src renders a broken-image icon - which is
    # exactly what the first build of this card produced, and is invisible unless you
    # look at the output rather than the exit code.
    faces = []
    for n in FACES:
        f = ROOT / "docs" / "faces" / f"{n}.jpg"
        if not f.exists():
            continue
        b64 = base64.b64encode(f.read_bytes()).decode()
        faces.append(f'<img src="data:image/jpeg;base64,{b64}">')
    faces = "".join(faces)
    return f"""<html><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1200px; height: 630px; background: #12100E; color: #E8E3DA;
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  padding: 62px 68px 0; display: flex; flex-direction: column;
  justify-content: space-between; overflow: hidden; }}
.mark {{ display: flex; align-items: center; gap: 20px; }}
.mark svg {{ width: 62px; height: 62px; color: #B98A4A; }}
h1 {{ font: 500 60px/1 ui-sans-serif, system-ui, "Segoe UI", sans-serif;
  letter-spacing: .16em; text-transform: uppercase; }}
p {{ font-size: 38px; line-height: 1.35; max-width: 21ch; color: #E8E3DA; }}
.strip {{ display: flex; gap: 0; margin: 0 -68px; }}
/* Bled to the edges and cropped to the top two-thirds of each portrait: at this size
   the faces are the recognisable part and the collars are not. */
/* invert() alone leaves each tile on pure black, which is a visible tonal step
   against the card's warm ground. screen() maps that black back onto the ground and
   leaves the white lines white, so the strip sits IN the card rather than on it. */
.strip img {{ width: 133.4px; height: 168px; object-fit: cover;
  object-position: 50% 22%; filter: invert(1); mix-blend-mode: screen;
  opacity: .93; }}
</style></head><body>
  <div class="mark">
    <svg viewBox="0 0 100 100">
      <path d="M30 78V46a20 20 0 0 1 40 0v32l-6.7-5.5-6.6 5.5-6.7-5.5-6.6 5.5-6.7-5.5z"
            fill="currentColor"/>
      <ellipse cx="42" cy="47" rx="4" ry="5" fill="#12100E"/>
      <ellipse cx="58" cy="47" rx="4" ry="5" fill="#12100E"/>
      <ellipse cx="50" cy="61" rx="3.4" ry="4.4" fill="#12100E"/>
    </svg>
    <h1>Ghostwriters</h1>
  </div>
  <p>We asked dead writers what they make of the modern world. They were not kind.</p>
  <div class="strip">{faces}</div>
</body></html>"""


def main() -> int:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=2)
        pg.set_content(html())
        pg.wait_for_timeout(400)
        raw = pg.screenshot()
        b.close()

    im = Image.open(_io.BytesIO(raw)).convert("RGB")
    big = len(raw)
    im = im.resize((1200, 630), Image.LANCZOS)
    im.quantize(colors=128, method=Image.MEDIANCUT).save(OUT, optimize=True)
    kb = OUT.stat().st_size // 1024
    print(f"{OUT}  1200x630 (drawn at 2x)  {big // 1024}KB -> {kb}KB")
    if kb > MAX_KB:
        print(f"FAIL: {kb}KB is over the {MAX_KB}KB WhatsApp renders reliably",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
