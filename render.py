"""Render the archive to static pages: an index, and one page per essay."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import voice

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{--ground:#12100E;--panel:#191614;--ink:#E8E3DA;--dim:#A39B8D;--faint:#6E665B;
  --rule:#2C2724;--accent:#B98A4A;--bad:#C4635A;--good:#7FA86A;
  --body:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
:root[data-theme="light"]{--ground:#F3F0EA;--panel:#FBF9F5;--ink:#1B1815;--dim:#5A5349;
  --faint:#8A8175;--rule:#DCD5C9;--accent:#8A5A1E;--bad:#A6402F;--good:#446E33}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ground);color:var(--ink);font:400 18px/1.68 var(--body)}
a{color:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.wrap{max-width:660px;margin:0 auto;padding:2.2rem 1.4rem 5rem}
.bar{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:2.2rem}
.home{order:2;font:500 13px/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;
  color:var(--dim);text-decoration:none;display:inline-flex;align-items:center;gap:0}
.home:hover{color:var(--accent)}
.home .back{color:var(--accent);font-size:14px;position:relative;top:-1px}
.tog{order:1;appearance:none;cursor:pointer;background:transparent;color:var(--dim);
  border:1px solid var(--rule);border-radius:999px;padding:.42rem .8rem;
  font:500 12px/1 var(--sans);letter-spacing:.04em}
.tog:hover{color:var(--ink);border-color:var(--accent)}
h1{font-weight:400;font-size:clamp(2rem,5.5vw,2.9rem);line-height:1.1;margin:0 0 .5rem;
  letter-spacing:-.01em;text-wrap:balance}
.stand{color:var(--dim);font-size:1.08rem;margin:0 0 2.6rem;max-width:46ch}
.eyebrow{font:600 11px/1 var(--sans);letter-spacing:.22em;text-transform:uppercase;
  color:var(--accent);margin:0 0 1.1rem}
.essay{margin-top:2.4rem}
.essay p{margin:0 0 1.35rem}
.essay p:first-of-type::first-letter{float:left;font-size:3.4rem;line-height:.86;
  padding:.06em .09em 0 0;color:var(--accent)}
.sortbar{display:flex;align-items:baseline;gap:.7rem;margin:0 0 .7rem;
  font:500 11px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase}
.sortbar span{color:var(--faint)}
.sortbar button{appearance:none;background:none;border:0;cursor:pointer;padding:.2rem 0;
  color:var(--dim);font:inherit;letter-spacing:inherit;text-transform:inherit;
  border-bottom:1px solid transparent}
.sortbar button:hover{color:var(--ink)}
.sortbar button[aria-pressed="true"]{color:var(--accent);border-bottom-color:var(--accent)}
/* Sits outside the underline so the rule under "Rating" does not grow a tail. */
.sortbar .dir:not(:empty){margin-left:.35em;font-size:11px}
.list{list-style:none;margin:0;padding:0}
.list li{border-top:1px solid var(--rule);padding:1.1rem 0}
.list li:last-child{border-bottom:1px solid var(--rule)}
/* Two columns, not a wrapping flex row. As a flex row a long title used the whole
   line and pushed the verdict onto its own, pinned to the far right with nothing
   beside it - "Michel de Montaigne on reclining a seat on a plane" did it at every
   width, since the column is capped at 660px. On a grid the title wraps inside its
   own column and the verdict stays on the first line where it belongs. */
.list a{text-decoration:none;display:grid;grid-template-columns:minmax(0,1fr) auto;
  column-gap:1.2rem;align-items:baseline}
.list a:hover .t{color:var(--accent)}
.rate{grid-column:2;grid-row:1;display:flex;align-items:baseline;gap:.55rem}
.rate .verdict{color:var(--faint);font:400 13px/1.4 var(--sans);text-align:right}
.rate .score{font:500 15px/1 var(--sans);font-variant-numeric:tabular-nums;
  min-width:2.4ch;text-align:right}
.s-bad{color:var(--bad)}
.s-mid{color:var(--accent)}
.s-good{color:var(--good)}
/* Under this width two columns leave the title too little to work with, so the row
   becomes one column and the verdict sits under the title. Left-aligned, not pinned
   to the far edge on its own, where it read as a stray caption rather than as part
   of the row. */
@media (max-width:620px){
  .list a{grid-template-columns:minmax(0,1fr)}
  .rate{grid-column:1;grid-row:auto;margin-top:.3rem;text-align:left}
  .rate .verdict{text-align:left}
}
.t{grid-column:1;grid-row:1;font-size:1.28rem}
/* The writer's name carries the row; the object it was set on sits back a shade. */
.t .thing{color:var(--dim)}
.list a:hover .thing{color:var(--accent)}
.foot{margin-top:3.4rem;color:var(--faint);font:400 13px/1.6 var(--sans)}
.foot + .foot{margin-top:.7rem}
.foot a{color:var(--dim)}
.tabs{display:flex;gap:1.5rem;margin:1.1rem 0 2.4rem;font:600 12px/1 var(--sans);
  letter-spacing:.14em;text-transform:uppercase}
.tabs a{color:var(--faint);text-decoration:none;padding-bottom:.4rem;border-bottom:2px solid transparent}
.tabs a:hover{color:var(--ink)}
.tabs a[aria-current]{color:var(--ink);border-bottom-color:var(--accent)}
/* A fourth tab does not fit at the desktop gap on a small phone: measured at 320px,
   294px of tabs into a 275px box, with "Guess" and half its underline off the right
   edge. The row is uppercase and letter-spaced, so the space between the words is
   where the slack is, not in the words. Applied at 400 rather than 320 because 375
   was fitting with nothing to spare. */
@media (max-width:400px){.tabs{gap:1rem;letter-spacing:.1em}}
.chips{display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 2.4rem;padding:0;list-style:none}
.chips a{display:inline-block;text-decoration:none;border:1px solid var(--rule);
  border-radius:999px;padding:.42rem .8rem;font:500 13px/1 var(--sans);color:var(--dim)}
.chips a:hover{color:var(--ink);border-color:var(--accent)}
.chips .n{color:var(--faint);font-size:11.5px}
.chips a{display:inline-flex;align-items:center;gap:.45rem}
.wordmark{display:flex;align-items:center;gap:.55rem}
.wordmark .ghost{flex:none;color:var(--ink);transition:transform .25s ease}
/* He floats when you hover him. Two seconds, eased both ways, a few pixels - a
   ghost bobbing, not a logo doing a trick. */
.wordmark:hover .ghost{animation:bob 2s ease-in-out infinite}
@keyframes bob{0%,100%{transform:translateY(0) rotate(0)}
  30%{transform:translateY(-13%) rotate(-4deg)}
  65%{transform:translateY(5%) rotate(3deg)}}
@media (prefers-reduced-motion:reduce){.wordmark:hover .ghost{animation:none}}
.face{border-radius:50%;flex:none;object-fit:cover;filter:saturate(.85)}
/* The portrait sits beside the title rather than over it under a label. */
.titled{display:flex;align-items:center;gap:1rem}
.titled .face{width:78px;height:78px}
/* NOT .back - the top bar already uses that for the arrow inside .home. */
.backlink{display:inline-flex;align-items:center;color:var(--dim);text-decoration:none;
  font:500 12px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;
  margin:0 0 1.4rem}
.backlink:hover{color:var(--accent)}
.backlink .arr{color:var(--accent);font-size:14px;position:relative;top:-1px}
.chips .face{width:26px;height:26px;margin:-3px 0}
/* The writers list carries a portrait, so it gets more room than the Subjects list.
   Two to a row on a fixed grid rather than content-width pills wrapping as they
   fall: shrink-to-fit gave a ragged column - one pill on some rows, two on others,
   every one a different length - and a roster reads as a roster only when the rows
   line up. The count is pushed to the pill's right edge so it makes a column too. */
.chips.people{display:grid;grid-template-columns:1fr 1fr;gap:.9rem}
.chips.people a,.chips.people .chip-off{display:flex;width:100%;height:78px;
  padding:0 .9rem 0 0;font-size:16px;gap:.8rem}
.chips.people .face{width:70px;height:70px;margin:0}
.chips.people .n{font-size:14px;margin-left:auto;padding-left:.5rem}
.chip-off .face{opacity:.35}
/* The column stops growing at 660px, so that is also where the two-up roster stops
   shrinking. Narrower than that and "David Foster Wallace" wraps inside its pill,
   so the grid drops to a single full-width row per writer instead. */
@media (max-width:660px){
  .chips.people{grid-template-columns:1fr;margin-bottom:2rem}
  .chips.people a,.chips.people .chip-off{height:74px;padding-right:1.2rem;font-size:17px}
  .chips.people .face{width:72px;height:72px}
}
/* Phones. The title portrait comes down so the heading is not squeezed into a
   two-word column beside it. */
@media (max-width:560px){
  .titled{gap:.8rem}
  .titled .face{width:58px;height:58px}
}
.chips .chip-off{display:inline-flex;align-items:center;gap:.45rem;border:1px dashed var(--rule);border-radius:999px;padding:.42rem .8rem;font:500 13px/1 var(--sans);color:var(--faint)}
/* --- Guess the writer ---------------------------------------------------
   The options are the same portrait pill as the writers roster, two to a row, on the
   same fixed grid, because they are the same thing: a list of writers to choose
   between. Colour here only ever means right or wrong, never decoration. */
.qprog{font:500 11px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;
  color:var(--faint);margin:0 0 1.2rem}
.qtext{margin:0 0 1.9rem;padding:0 0 0 1.1rem;border-left:2px solid var(--rule);
  font-size:1.12rem}
.opts{display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin:0 0 1.5rem;
  padding:0;list-style:none}
.opts button{display:flex;align-items:center;gap:.8rem;width:100%;height:66px;
  padding:0 .9rem 0 0;appearance:none;cursor:pointer;background:transparent;
  color:var(--dim);border:1px solid var(--rule);border-radius:999px;
  font:500 15px/1.25 var(--sans);text-align:left}
.opts button.plain{padding-left:1.1rem}
.opts button .face{width:58px;height:58px;margin:0 0 0 3px}
.opts button:hover:not(:disabled){color:var(--ink);border-color:var(--accent)}
.opts button:disabled{cursor:default}
.opts button.is-right{color:var(--good);border-color:var(--good)}
.opts button.is-wrong{color:var(--bad);border-color:var(--bad)}
.qafter{display:flex;align-items:center;justify-content:space-between;gap:1rem;
  flex-wrap:wrap;min-height:2.6rem}
.qafter a{color:var(--dim);font:400 14px/1.5 var(--sans)}
.qbtn{appearance:none;cursor:pointer;background:transparent;color:var(--accent);
  border:1px solid var(--accent);border-radius:999px;padding:.52rem 1.1rem;
  font:500 12px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase}
.qbtn:hover{background:var(--panel)}
.qscore{font-size:1.5rem;margin:0 0 1.6rem}
.qscore + .list{margin-bottom:2rem}
@media (max-width:520px){
  .opts{grid-template-columns:1fr}
  .opts button{height:62px}
}
"""

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:site_name" content="Ghostwriters">
<!-- ABSOLUTE, not {up}og.png. WhatsApp does not resolve a relative og:image, which is
     why a card can look right in a local preview and show nothing in a chat. Same for
     og:url - without it a share of an essay page attributes to no canonical address.
     Built by tools/make_og.py, which fails rather than shipping a file over the size
     WhatsApp will render. -->
<meta property="og:image" content="{SITE}og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Ghostwriters - nine ink portraits of dead writers">
<meta property="og:url" content="{SITE}{canon}">
<link rel="canonical" href="{SITE}{canon}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{up}favicon.svg" type="image/svg+xml">
<link rel="icon" href="{up}favicon.ico" sizes="any">
<link rel="icon" href="{up}favicon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="{up}apple-touch-icon.png">
<script>
  (function(){{try{{var s=localStorage.getItem("dy-theme");
    document.documentElement.setAttribute("data-theme",s==="light"?"light":"dark");}}
    catch(e){{document.documentElement.setAttribute("data-theme","dark");}}}})();
</script>
<style>{css}</style>
<!-- Analytics, gated. Two kinds of visitor are not an audience and never load it:
     anyone who has opted out with ?nostats=1, and automation, since navigator.webdriver
     is the one signal true for Playwright, Puppeteer and Selenium alike. Inline and
     dependency-free on purpose - served from the Worker, a bad deploy there would stop
     analytics on every site. Braces are doubled because HEAD goes through .format().
     See site-stats/beacon. -->
<script>(function(){{try{{var X="ct.nostats",C="ct_nostats",D=";path=/;domain=.charlietrenorden.com",q=location.search,out=false;if(q.indexOf("nostats=1")>-1){{try{{localStorage.setItem(X,"1")}}catch(e){{}}document.cookie=C+"=1"+D+";max-age=63072000;samesite=lax";}}if(q.indexOf("nostats=0")>-1){{try{{localStorage.removeItem(X)}}catch(e){{}}document.cookie=C+"="+D+";max-age=0";}}try{{out=!!localStorage.getItem(X)}}catch(e){{}}if(!out)out=document.cookie.indexOf(C+"=1")>-1;if(out||navigator.webdriver)return;var d=document,s;s=d.createElement("script");s.defer=true;s.src="https://static.cloudflareinsights.com/beacon.min.js";s.setAttribute("data-cf-beacon",'{{"token": "32b821209b5441a08df42ccf61c9e6c2"}}');d.head.appendChild(s);s=d.createElement("script");s.defer=true;s.src="https://beacon.charlietrenorden.com/b.js";d.head.appendChild(s);}}catch(e){{}}}})();</script>
</head>
<body>
<div class="wrap">
  <div class="bar">
    <a class="home" href="https://charlietrenorden.com/"><span class="back">&larr;</span>&nbsp;Other projects</a>
    <button class="tog" id="tog" type="button">Light</button>
  </div>
"""

TAIL = """
  <p class="foot">FOOTER</p>
</div>
<script>
  (function(){
    var r=document.documentElement,b=document.getElementById("tog");
    function sync(){b.textContent=r.getAttribute("data-theme")==="dark"?"Light":"Dark";}
    sync();
    b.addEventListener("click",function(){
      var light=r.getAttribute("data-theme")!=="light";
      r.setAttribute("data-theme",light?"light":"dark");
      try{localStorage.setItem("dy-theme",light?"light":"dark");}catch(e){}
      sync();
    });
  })();
</script>
</body>
</html>
"""


# The ghost from favicon.svg, inline so it can sit beside the title and take the
# theme. Two shapes and two dots - the same reason the favicon works at 16px.
GHOST = ('<svg class="ghost" viewBox="0 0 100 100" width="1.28em" height="1.28em" aria-hidden="true">'
         '<path d="M30 78V46a20 20 0 0 1 40 0v32l-6.7-5.5-6.6 5.5-6.7-5.5-6.6 5.5-6.7-5.5z" fill="currentColor"/>'
         '<ellipse cx="42" cy="47" rx="4" ry="5" fill="var(--ground)"/>'
         '<ellipse cx="58" cy="47" rx="4" ry="5" fill="var(--ground)"/>'
         '<ellipse cx="50" cy="61" rx="3.4" ry="4.4" fill="var(--ground)"/></svg>')


def nav(up: str, here: str) -> str:
    """Three ways in: newest first, by writer, by object. Rendered on every page so
    the site is browsable from wherever you land, not only from the front page."""
    items = [("index", "Latest", f"{up}index.html"),
             ("writers", "Writers", f"{up}writers.html"),
             ("objects", "Subjects", f"{up}objects.html"),
             ("guess", "Guess", f"{up}guess.html")]
    out = ['  <nav class="tabs">']
    for key, label, href in items:
        cur = ' aria-current="page"' if key == here else ""
        out.append(f'<a href="{href}"{cur}>{label}</a>')
    out.append("</nav>")
    return "".join(out) + "\n"


def face(tid: str, prefix: str, size: int) -> str:
    """The portrait, or nothing at all if it has not been drawn yet.

    Adding a writer is two commits: styles/ and the essays are cheap, the portrait
    needs the image tier, which is metered and often spent by the evening. Without
    this check the writers page carries a broken-image icon for however long that
    gap lasts. An absent face is a missing ornament; a broken one looks like a
    broken site."""
    if not (DOCS / "faces" / f"{tid}.jpg").exists():
        return ""
    return (f'<img class="face" src="{prefix}faces/{tid}.jpg" alt="" '
            f'width="{size}" height="{size}" loading="lazy">')


def slug(entry: dict) -> str:
    o = "".join(c if c.isalnum() else "-" for c in entry["object"].lower())
    return f'{entry["date"]}-{entry["thinker"]}-{o.strip("-")[:40]}'


def paragraphs(essay: str) -> str:
    """The model returns one block. Break it into three-ish paragraphs on sentence
    boundaries so the page is readable rather than a wall of text.

    The boundaries come from voice.sentences rather than a local regex, because this
    module had its own copy and it broke after any full stop at all - so a title or an
    initial started a new paragraph mid-sentence."""
    sents = voice.sentences(essay)
    if len(sents) < 4:
        return f"<p>{html.escape(essay)}</p>"
    per = max(2, round(len(sents) / 3))
    out, buf = [], []
    for s in sents:
        buf.append(s)
        if len(buf) >= per:
            out.append(" ".join(buf))
            buf = []
    if buf:
        if len(buf) == 1 and out:
            out[-1] += " " + buf[0]
        else:
            out.append(" ".join(buf))
    return "\n    ".join(f"<p>{html.escape(p)}</p>" for p in out)


def extract(essay: str, target: int = 55, cap: int = 5) -> str:
    """The passage the guessing game shows: whole sentences from the top, until it
    has enough words to have a voice in it.

    Whole sentences because the tells are cadence and where a clause turns, and a
    passage cut mid-clause takes exactly that away. It starts at the first sentence
    rather than skipping in: the opening is where these writers are most themselves,
    and the shortest essay here is 129 words, so there is always more after it.

    Split with voice.sentences, never a local regex - a plain split on a full stop
    breaks after an initial or a title, and Kafka's essays are full of both."""
    out, n = [], 0
    for s in voice.sentences(essay):
        out.append(s)
        n += len(s.split())
        if n >= target or len(out) >= cap:
            break
    return clip(" ".join(out))


# Whole sentences would be the whole essay for the writers who work in one long one:
# Proust on painkillers ran 207 words to its first full stop, out of an essay of 220.
# That gives the passage away twice over - it leaves nothing to click through to, and
# a block four times the length of the others is a tell in itself.
HARD = 110
_BREAK = re.compile(r"[,;:]")


def clip(passage: str) -> str:
    """Cut an over-long passage at a clause boundary and leave it visibly unfinished.

    The obvious alternative, dropping that sentence and taking a shorter one, is wrong
    here: an unbroken sentence IS the fingerprint for Proust, Wallace and Whitman, so
    it would remove the evidence from exactly the writers who are easiest to spot. A
    sentence still running at the ellipsis says the same thing in a quarter the space."""
    words = passage.split()
    if len(words) <= HARD:
        return passage
    head = " ".join(words[:HARD])
    cuts = [m.end() for m in _BREAK.finditer(head)]
    # Only honour a clause break in the back half; an early comma would throw most of
    # the passage away to save a few words.
    if cuts and cuts[-1] > len(head) * 0.6:
        head = head[:cuts[-1] - 1]
    return head.rstrip(",;: ") + "…"


def guess_data(entries: list[dict], roster: list[dict] | None) -> dict:
    """Everything the game needs, in one blob: the roster it draws options from, and
    one passage per published essay.

    Every writer in the roster is an option, including any with nothing published yet.
    A writer who could never be the answer would be learnable as one to rule out,
    which is a way of scoring that has nothing to do with reading the prose."""
    ids = [t["id"] for t in (roster or [])] or sorted({e["thinker"] for e in entries})
    names = {e["thinker"]: e["name"] for e in entries}
    names.update({t["id"]: t["name"] for t in (roster or [])})
    idx = {tid: i for i, tid in enumerate(ids)}
    return {
        "writers": [{"id": t, "name": names.get(t, t),
                     "face": (DOCS / "faces" / f"{t}.jpg").exists()} for t in ids],
        "qs": [{"t": extract(e["essay"]), "w": idx[e["thinker"]],
                "e": slug(e), "o": e["object"]}
               for e in entries if e["thinker"] in idx],
    }


def obj_slug(obj: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in obj.lower()).strip("-")[:50]


def essay_rows(entries, up="", show="both") -> str:
    """A list of essays. `show` drops whichever half is already the page's heading -
    on a writer's page every row says the same name, and on an object's page every
    row says the same object."""
    rows = []
    for e in reversed(entries):
        # NO SECOND LINE ON ANY OF THEM. It used to print the writer's name under
        # each row of a writer's own page, which is the name the h1 two inches above
        # is already carrying - the exact repetition the docstring says this argument
        # exists to prevent, and it shipped on all 18 writer pages. There is nothing
        # left for it to carry: a writer's years and the day a machine generated the
        # essay were both ruled out as noise, and the object is already the title.
        if show == "object":
            t = html.escape(e["object"])
        elif show == "writer":
            t = html.escape(e["name"])
        else:
            t = (f'{html.escape(e["name"])} '
                 f'<span class="thing">on {html.escape(e["object"])}</span>')
        # What the writer made of it, and how much out of ten. Not on a writer's own
        # page, where a column of their own scores is a chart nobody asked for; a
        # subject page is the same comparison the front page makes, so it keeps it.
        rate = ""
        if show in ("both", "writer") and e.get("score") is not None:
            band = "s-bad" if e["score"] < 3.5 else "s-good" if e["score"] > 6.5 else "s-mid"
            rate = (f'<span class="rate"><span class="verdict">'
                    f'{html.escape(e.get("verdict", ""))}</span>'
                    f'<span class="score {band}">{e["score"]:.1f}</span></span>')
        # data-score lets the front page sort client-side; data-seq preserves the
        # published order so "latest" can be restored exactly rather than guessed.
        ds = "" if e.get("score") is None else f' data-score="{e["score"]:.1f}"'
        rows.append(
            f'    <li{ds} data-seq="{len(rows)}"><a href="{up}e/{slug(e)}.html">'
            f'<span class="t">{t}</span>' + rate + "</a></li>")
    return "\n".join(rows)


SORT_JS = """
<script>
/* Reorder the front-page list in place. Latest is the order the pages were built
   in, kept on each row as data-seq, so switching back restores it exactly rather
   than re-deriving it from dates that several essays share.

   Rating TOGGLES. Clicking it again turns the list over, worst first, because the
   bad ones are half the fun and there was no way to reach them without scrolling to
   the bottom. The direction shows as an arrow on the button rather than as a second
   control or a changed word: one thing to click, and its state is visible. Newest
   does not toggle - "oldest first" is a different question nobody asked, and a bar
   where one button has a hidden second state and the other does not would be worse
   than either. */
(function () {
  var bar = document.querySelector('.sortbar');
  var list = document.getElementById('all');
  if (!bar || !list) return;
  var rows = Array.prototype.slice.call(list.children);
  var asc = false;                       /* rating: high to low first */
  bar.addEventListener('click', function (ev) {
    var btn = ev.target.closest('button[data-sort]');
    if (!btn) return;
    var key = btn.dataset.sort;
    /* Only a second click on the button that is ALREADY pressed flips it. Arriving
       from Newest gives high-to-low, which is what someone asking for a rating
       expects to see first. */
    asc = (key === 'score' && btn.getAttribute('aria-pressed') === 'true') ? !asc : false;
    bar.querySelectorAll('button[data-sort]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b === btn));
      var arrow = b.querySelector('.dir');
      if (arrow) arrow.textContent = (b === btn && key === 'score')
        ? (asc ? '↑' : '↓') : '';
    });
    var sorted = rows.slice().sort(function (a, b) {
      if (key === 'score') {
        /* An unscored essay sorts LAST in both directions rather than as a zero,
           which would put it below a genuine 0.5 going down and at the very top
           going up - the one row nobody is looking for, twice. */
        var ua = a.dataset.score === undefined, ub = b.dataset.score === undefined;
        if (ua !== ub) return ua ? 1 : -1;
        if (!ua) {
          var sa = parseFloat(a.dataset.score), sb = parseFloat(b.dataset.score);
          if (sa !== sb) return asc ? sa - sb : sb - sa;
        }
      }
      return (+a.dataset.seq) - (+b.dataset.seq);
    });
    var frag = document.createDocumentFragment();
    sorted.forEach(function (r) { frag.appendChild(r); });
    list.appendChild(frag);
  });
})();
</script>
"""


GUESS_JS = """
<script>
/* Guess the writer. Ten passages, four names under each, and a link into the essay
   once you have answered.

   The round is drawn fresh on every load rather than fixed at build time, so the page
   is worth opening twice. Nothing is stored: a score kept in localStorage would turn a
   two-minute game into a record you can spoil by reloading. */
(function () {
  var root = document.getElementById('quiz');
  var blob = document.getElementById('quiz-data');
  if (!root || !blob) return;
  var data = JSON.parse(blob.textContent);
  var ROUND = Math.min(10, data.qs.length);
  var order, at, right, log;

  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1)), t = a[i];
      a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function pill(w) {
    /* The same portrait pill as the writers roster. A writer whose portrait has not
       been drawn yet gets the name alone rather than a broken image. */
    var b = el('button', w.face ? '' : 'plain');
    b.type = 'button';
    if (w.face) {
      var img = document.createElement('img');
      img.className = 'face'; img.src = 'faces/' + w.id + '.jpg'; img.alt = '';
      img.width = 58; img.height = 58; img.loading = 'lazy';
      b.appendChild(img);
    }
    b.appendChild(document.createTextNode(w.name));
    return b;
  }

  function start() {
    order = shuffle(data.qs.map(function (_, i) { return i; })).slice(0, ROUND);
    at = 0; right = 0; log = [];
    ask();
  }

  function prog() {
    /* Redrawn on the answer as well as on the question. Left to the question alone
       it lagged a step: you got one right, a green tick said so, and the counter
       above it still read 0. A running total that is only right between turns is
       not a running total. */
    root.querySelector('.qprog').textContent =
      (at + 1) + ' of ' + ROUND + ' \\u00b7 ' + right + ' right';
  }

  function ask() {
    var q = data.qs[order[at]];
    var pool = data.writers.map(function (_, i) { return i; })
      .filter(function (i) { return i !== q.w; });
    var opts = shuffle(shuffle(pool).slice(0, 3).concat([q.w]));

    root.textContent = '';
    root.appendChild(el('p', 'qprog', ''));
    prog();
    root.appendChild(el('blockquote', 'qtext', q.t));

    var box = el('div', 'opts');
    opts.forEach(function (i) {
      var b = pill(data.writers[i]);
      b.addEventListener('click', function () { answer(q, i, box); });
      box.appendChild(b);
    });
    root.appendChild(box);
    root.appendChild(el('div', 'qafter'));
  }

  function answer(q, picked, box) {
    var hit = picked === q.w;
    if (hit) right++;
    log.push({ q: q, picked: picked, hit: hit });
    prog();

    /* Mark the answer green wherever it is, and the wrong pick red. Both, so a wrong
       guess still tells you who it actually was. */
    Array.prototype.forEach.call(box.children, function (b) {
      b.disabled = true;
      var name = b.textContent;
      if (name === data.writers[q.w].name) b.classList.add('is-right');
      else if (!hit && name === data.writers[picked].name) b.classList.add('is-wrong');
    });

    var after = root.querySelector('.qafter');
    after.setAttribute('role', 'status');
    var link = document.createElement('a');
    link.href = 'e/' + q.e + '.html';
    link.textContent = data.writers[q.w].name + ' on ' + q.o;
    after.appendChild(link);
    var next = el('button', 'qbtn', at + 1 < ROUND ? 'Next' : 'How you did');
    next.type = 'button';
    next.addEventListener('click', function () {
      at++;
      if (at < ROUND) ask(); else done();
    });
    after.appendChild(next);
    next.focus();
  }

  function done() {
    root.textContent = '';
    root.appendChild(el('p', 'qscore', 'You got ' + right + ' of ' + ROUND + '.'));
    var ul = el('ul', 'list');
    log.forEach(function (r) {
      var w = data.writers[r.q.w];
      ul.insertAdjacentHTML('beforeend',
        '<li><a href="e/' + esc(r.q.e) + '.html"><span class="t">' + esc(w.name) +
        ' <span class="thing">on ' + esc(r.q.o) + '</span></span>' +
        '<span class="rate"><span class="verdict">' +
        (r.hit ? '' : 'you said ' + esc(data.writers[r.picked].name)) +
        '</span><span class="score ' + (r.hit ? 's-good' : 's-bad') + '">' +
        (r.hit ? '\\u2713' : '\\u2717') + '</span></span></a></li>');
    });
    root.appendChild(ul);
    var again = el('button', 'qbtn', 'Play again');
    again.type = 'button';
    again.addEventListener('click', start);
    root.appendChild(again);
    /* Deliberately NOT again.focus(). Focusing the button scrolls it into view, and
       it sits under ten rows: on a phone that lands the reader at the bottom of the
       list with their score off the top of the screen, which is the one thing they
       just asked to see. Scroll only when the score is genuinely above the fold. */
    if (root.getBoundingClientRect().top < 0) root.scrollIntoView({ block: 'start' });
  }

  start();
})();
</script>
"""


SITE = "https://charlietrenorden.com/ghostwriters/"


def page(title, desc, body, up, here, footer, canon=""):
    """`body` carries its own <h1>; the nav is injected straight after it, so the
    heading comes first and the three ways in sit under it.

    `canon` is the page's path below SITE - "" for the front page, "e/<slug>.html" for
    an essay. It feeds og:url and rel=canonical, both of which must be ABSOLUTE: a
    share of an essay otherwise attributes to no address at all."""
    if here and "</h1>" in body:
        head_end = body.index("</h1>") + len("</h1>") + 1
        body = body[:head_end] + nav(up, here) + body[head_end:]
    tail = TAIL.replace("FOOTER", footer)
    # Only the front page carries the sort control, so only it carries the script.
    if 'class="sortbar"' in body:
        tail = SORT_JS + tail
    if 'id="quiz"' in body:
        tail = GUESS_JS + tail
    return (HEAD.format(title=html.escape(title), desc=html.escape(desc), css=CSS, up=up,
                        SITE=SITE, canon=canon)
            + body + tail)


def build(entries: list[dict], roster: list[dict] | None = None) -> None:
    DOCS.mkdir(exist_ok=True)
    for sub in ("e", "by", "on"):
        (DOCS / sub).mkdir(exist_ok=True)

    # Remove any generated page this build does not produce. Without this the
    # renderer only ever ADDS: a page written by an earlier run - a test, a
    # renamed object, a deleted essay - survives forever and stays reachable by
    # URL. That happened on 25/08/2026: a render test wrote three synthetic essay
    # pages, the rebuild left them in place, and they went live. Whatever is not
    # in `entries` is not real, so it should not exist on disk.
    keep = {DOCS / "e" / f"{slug(e)}.html" for e in entries}
    keep |= {DOCS / "by" / f'{e["thinker"]}.html' for e in entries}
    keep |= {DOCS / "on" / f'{obj_slug(e["object"])}.html' for e in entries}
    for sub in ("e", "by", "on"):
        for f in (DOCS / sub).glob("*.html"):
            if f not in keep:
                print(f"  pruned stale page {sub}/{f.name}")
                f.unlink()

    # Every list of WRITERS on the site files by surname, not just the Writers page:
    # the "Also on <subject>" line under an essay and the sentence in a subject page's
    # meta description are lists of authors too, and a roster that sorts one way while
    # its own cross-references sort another reads as an oversight. The essays carry an
    # id and a display name, so the sort key has to come from the roster; without one
    # this falls back to the display name rather than refusing to render.
    sort_of = {t["id"]: (t.get("sort") or t["name"]) for t in (roster or [])}

    def by_surname(es):
        return sorted(es, key=lambda x: sort_of.get(x["thinker"], x["name"]).lower())

    by_writer, by_object = {}, {}
    for e in entries:
        by_writer.setdefault(e["thinker"], []).append(e)
        by_object.setdefault(e["object"], []).append(e)

    # --- one page per essay -------------------------------------------------
    for e in entries:
        others = by_surname([x for x in by_object[e["object"]] if x is not e])
        also = ""
        if others:
            # The point of the object axis: who ELSE has been set on this thing.
            links = ", ".join(f'<a href="../e/{slug(x)}.html">{html.escape(x["name"])}</a>'
                              for x in others)
            also = f'  <p class="foot">Also on {html.escape(e["object"])}: {links}.</p>\n'
        body = ('  <a class="backlink" href="../index.html">'
                '<span class="arr">&larr;</span>&nbsp;All the essays</a>\n'
                f'  <h1 class="titled">{face(e["thinker"], "../", 76)}<span>'
                f'<a href="../by/{e["thinker"]}.html" style="text-decoration:none">'
                f'{html.escape(e["name"])}</a> on '
                f'<a href="../on/{obj_slug(e["object"])}.html" style="text-decoration:none">'
                f'{html.escape(e["object"])}</a></span></h1>\n'
                f'  <div class="essay">\n    {paragraphs(e["essay"])}\n  </div>\n'
                + also)
        p = page(f'{e["name"]} on {e["object"]}',
                 f'A pastiche essay in the style of {e["name"]} about {e["object"]}, '
                 'which they never saw.',
                 body, "../", "", "", canon=f"e/{slug(e)}.html")
        (DOCS / "e" / f"{slug(e)}.html").write_text(p, encoding="utf-8", newline="\n")

    # --- one page per writer ------------------------------------------------
    for tid, es in by_writer.items():
        name, dates = es[0]["name"], es[0]["dates"]
        body = (f'  <h1 class="titled">{face(tid, "../", 76)}'
                f'<span>{html.escape(name)}</span></h1>\n'
                f'  <ul class="list">\n{essay_rows(es, "../", show="object")}\n  </ul>\n')
        p = page(f"{name} - Ghostwriters",
                 f"Pastiche essays in the style of {name} about things that did not exist "
                 "in their lifetime.", body, "../", "writers",
                 "", canon=f"by/{tid}.html")
        (DOCS / "by" / f"{tid}.html").write_text(p, encoding="utf-8", newline="\n")

    # --- one page per object: everyone who has been set on it ---------------
    for obj, es in by_object.items():
        names = [x["name"] for x in by_surname(es)]
        who = " and ".join([", ".join(names[:-1]), names[-1]]).strip(", ")
        # The rows are the front page's rows verbatim - name, object, verdict, score.
        body = (f'  <h1>{html.escape(obj)}</h1>\n'
                f'  <ul class="list">\n{essay_rows(es, "../")}\n  </ul>\n')
        p = page(f"{obj} - Ghostwriters",
                 f"{who} on {obj}, in pastiche.", body, "../", "objects", "",
                 canon=f"on/{obj_slug(obj)}.html")
        (DOCS / "on" / f"{obj_slug(obj)}.html").write_text(p, encoding="utf-8", newline="\n")

    # --- the three top-level views ------------------------------------------
    desc = ("We asked dead writers what they make of the modern world. "
            "They were not kind.")
    listing = f'  <ul class="list" id="all">\n{essay_rows(entries)}\n  </ul>\n' if entries else ""
    # Sorting is the only interactive thing on this page, so it is two buttons and
    # no framework. The default is the published order, newest first, which is what
    # the page has always shown and what someone arriving expects to see.
    #
    # "Newest" rather than "Latest" because Latest is the name of the nav tab
    # directly above it, and the same word twice in two stacked bars reads as a
    # cross-reference to the other page rather than as a sort order.
    sortbar = ('  <div class="sortbar">\n    <span>Sort</span>\n    <button type="button" data-sort="seq" aria-pressed="true">Newest</button>\n    <button type="button" data-sort="score" aria-pressed="false">Rating<span class="dir"></span></button>\n  </div>\n') if entries else ""
    idx = (f'  <h1 class="wordmark">{GHOST}Ghostwriters</h1>\n'
           f'  <p class="stand">{html.escape(desc)}</p>\n' + sortbar + listing)
    (DOCS / "index.html").write_text(
        page("Ghostwriters", desc, idx, "", "index",
             ""),
        encoding="utf-8", newline="\n")

    # The whole roster, not only the writers who happen to have published. A name
    # with a nought beside it is information: it is in the rotation, not yet drawn.
    # styles.load() already returns the roster by SURNAME - the name a reader holds a
    # writer by - so this iterates it rather than re-sorting on the display name, which
    # is what put David Foster Wallace beside Douglas Adams. The fallback has no sort
    # key to work with and keeps the display name.
    # t.get("sort") rather than t["sort"]: styles.load() guarantees the key and
    # tests/test_roster.py enforces it, but a roster built by hand - a test fixture, a
    # one-off script - should not have to know about it to render a page.
    listed = ([(t["id"], t["name"], len(by_writer.get(t["id"], [])),
                t.get("sort") or t["name"]) for t in roster]
              if roster else
              sorted(((k, v[0]["name"], len(v), v[0]["name"])
                      for k, v in by_writer.items()), key=lambda x: x[3].lower()))
    chips = "\n".join(
        (f'    <li><a href="by/{tid}.html">'
         f'{face(tid, "", 86)}'
         f'{html.escape(name)} <span class="n">{n}</span></a></li>') if n else
        (f'    <li><span class="chip-off">'
         f'{face(tid, "", 86)}'
         f'{html.escape(name)} <span class="n">0</span></span></li>')
        for tid, name, n, _ in listed)
    (DOCS / "writers.html").write_text(
        page("Writers - Ghostwriters",
             "Every writer in the rotation, and how many essays each has.",
             '  <h1>Writers</h1>\n'
             f'  <ul class="chips people">\n{chips}\n  </ul>\n', "", "writers",
             "", canon="writers.html"),
        encoding="utf-8", newline="\n")

    # --- guess the writer ---------------------------------------------------
    # Four options means four writers to draw from, and a passage means an essay.
    # Below either, this would be a game that cannot be played, so it is not written
    # at all and any copy an earlier run left behind is removed.
    gd = guess_data(entries, roster)
    if len(gd["writers"]) >= 4 and gd["qs"]:
        gdesc = "Read a passage and pick which of the writers wrote it."
        gbody = ('  <h1>Guess the Writer</h1>\n'
                 f'  <p class="stand">{len(gd["qs"])} essays, and none of them '
                 'signed.</p>\n'
                 '  <div id="quiz"><noscript>This one needs JavaScript. '
                 '<a href="index.html">The essays</a> do not.</noscript></div>\n'
                 '  <script type="application/json" id="quiz-data">'
                 # Escaped so a `</script>` in an essay cannot close the block early
                 # and take the whole game down with it. What a model writes at night
                 # is not something the renderer gets to assume about.
                 + json.dumps(gd, ensure_ascii=False).replace("<", "\\u003c")
                 + '</script>\n')
        (DOCS / "guess.html").write_text(
            page("Guess the Writer - Ghostwriters", gdesc, gbody, "", "guess", "",
                 canon="guess.html"),
            encoding="utf-8", newline="\n")
    elif (DOCS / "guess.html").exists():
        (DOCS / "guess.html").unlink()
        print("  pruned guess.html - not enough writers or essays to play")

    ochips = "\n".join(
        f'    <li><a href="on/{obj_slug(o)}.html">{html.escape(o)} '
        f'<span class="n">{len(es)}</span></a></li>'
        for o, es in sorted(by_object.items()))
    (DOCS / "objects.html").write_text(
        page("Subjects - Ghostwriters",
             "Every subject written about here, and how many writers have been set on it.",
             '  <h1>Subjects</h1>\n'
             f'  <ul class="chips">\n{ochips}\n  </ul>\n', "", "objects",
             "", canon="objects.html"),
        encoding="utf-8", newline="\n")
