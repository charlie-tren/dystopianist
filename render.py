"""Render the archive to static pages: an index, and one page per essay."""
from __future__ import annotations

import html
import re
from pathlib import Path

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
.sortbar{display:flex;align-items:baseline;gap:.7rem;margin:0 0 .2rem;
  font:500 11px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase}
.sortbar span{color:var(--faint)}
.sortbar button{appearance:none;background:none;border:0;cursor:pointer;padding:.2rem 0;
  color:var(--dim);font:inherit;letter-spacing:inherit;text-transform:inherit;
  border-bottom:1px solid transparent}
.sortbar button:hover{color:var(--ink)}
.sortbar button[aria-pressed="true"]{color:var(--accent);border-bottom-color:var(--accent)}
.list{list-style:none;margin:0;padding:0}
.list li{border-top:1px solid var(--rule);padding:1.1rem 0}
.list li:last-child{border-bottom:1px solid var(--rule)}
.list a{text-decoration:none;display:flex;flex-wrap:wrap;align-items:baseline;
  gap:.4rem 1.2rem;justify-content:space-between}
.list a:hover .t{color:var(--accent)}
.rate{flex:none;display:flex;align-items:baseline;gap:.55rem;margin-left:auto}
.rate .verdict{color:var(--faint);font:400 13px/1.4 var(--sans);text-align:right}
.rate .score{font:500 15px/1 var(--sans);font-variant-numeric:tabular-nums;
  min-width:2.4ch;text-align:right}
.s-bad{color:var(--bad)}
.s-mid{color:var(--accent)}
.s-good{color:var(--good)}
/* Under this width the title takes the whole line and the verdict wraps below it.
   Pinned right by margin-left:auto it landed against the far edge on its own,
   which read as a stray caption rather than as part of the row. Left-aligned it
   sits under the title and the two lines read as one thing. */
@media (max-width:620px){
  .rate{margin-left:0;text-align:left}
  .rate .verdict{text-align:left}
}
.t{font-size:1.28rem}
/* The writer's name carries the row; the object it was set on sits back a shade. */
.t .thing{color:var(--dim)}
.list a:hover .thing{color:var(--accent)}
/* A span, so its margin-top did nothing and it ran straight on from the title.
   It only shows on the writer and object pages, which is why the index hid it. */
.sub{display:block;color:var(--faint);font:400 13.5px/1.5 var(--sans);margin-top:.25rem}
.foot{margin-top:3.4rem;color:var(--faint);font:400 13px/1.6 var(--sans)}
.foot + .foot{margin-top:.7rem}
.foot a{color:var(--dim)}
.tabs{display:flex;gap:1.5rem;margin:1.1rem 0 2.4rem;font:600 12px/1 var(--sans);
  letter-spacing:.14em;text-transform:uppercase}
.tabs a{color:var(--faint);text-decoration:none;padding-bottom:.4rem;border-bottom:2px solid transparent}
.tabs a:hover{color:var(--ink)}
.tabs a[aria-current]{color:var(--ink);border-bottom-color:var(--accent)}
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
/* The writers list carries a portrait, so it gets more room than the Subjects list. */
.chips.people a,.chips.people .chip-off{padding:0 1.7rem 0 0;height:88px;
  font-size:18px;gap:1.15rem}
.chips.people{gap:.9rem}
.chips.people .face{width:86px;height:86px;margin:0}
.chips.people .n{font-size:14px}
.chip-off .face{opacity:.35}
/* Phones. Content-width pills leave ragged trailing space in a narrow column and a
   long name wraps inside one, so the writers become full-width rows with the count
   pushed right; and the title portrait comes down so the heading is not squeezed
   into a two-word column beside it. */
@media (max-width:560px){
  .chips.people{display:block;margin-bottom:2rem}
  .chips.people li{margin-bottom:.7rem}
  .chips.people a,.chips.people .chip-off{display:flex;width:100%;height:74px;
    font-size:17px;padding-right:1.2rem}
  .chips.people .face{width:72px;height:72px}
  .chips.people .n{margin-left:auto}
  .titled{gap:.8rem}
  .titled .face{width:58px;height:58px}
}
.chips .chip-off{display:inline-flex;align-items:center;gap:.45rem;border:1px dashed var(--rule);border-radius:999px;padding:.42rem .8rem;font:500 13px/1 var(--sans);color:var(--faint)}
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
<!-- Cloudflare Web Analytics - same estate-wide token as the hub root. -->
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "32b821209b5441a08df42ccf61c9e6c2"}}'></script>
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
             ("objects", "Subjects", f"{up}objects.html")]
    out = ['  <nav class="tabs">']
    for key, label, href in items:
        cur = ' aria-current="page"' if key == here else ""
        out.append(f'<a href="{href}"{cur}>{label}</a>')
    out.append("</nav>")
    return "".join(out) + "\n"


def slug(entry: dict) -> str:
    o = "".join(c if c.isalnum() else "-" for c in entry["object"].lower())
    return f'{entry["date"]}-{entry["thinker"]}-{o.strip("-")[:40]}'


def paragraphs(essay: str) -> str:
    """The model returns one block. Break it into three-ish paragraphs on sentence
    boundaries so the page is readable rather than a wall of text."""
    sents = re.split(r"(?<=[.!?])\s+", essay.strip())
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


def obj_slug(obj: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in obj.lower()).strip("-")[:50]


def essay_rows(entries, up="", show="both") -> str:
    """A list of essays. `show` drops whichever half is already the page's heading -
    on a writer's page every row says the same name, and on an object's page every
    row says the same object."""
    rows = []
    for e in reversed(entries):
        # the sub-line carries whichever half the heading does not. No dates: a
        # writer's years and the day a machine generated the essay are both noise.
        # Nothing on a subject page: the heading is the object, so a row reading
        # "Marcus Aurelius / escape rooms" says it twice. That page is meant to
        # read like the front page - a name and a score.
        sub = {"object": e["name"]}.get(show, "")
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
            f'<span class="t">{t}</span>'
            + (f'<span class="sub">{html.escape(sub)}</span>' if sub else "")
            + rate + "</a></li>")
    return "\n".join(rows)


SORT_JS = """
<script>
/* Reorder the front-page list in place. Latest is the order the pages were built
   in, kept on each row as data-seq, so switching back restores it exactly rather
   than re-deriving it from dates that several essays share. */
(function () {
  var bar = document.querySelector('.sortbar');
  var list = document.getElementById('all');
  if (!bar || !list) return;
  var rows = Array.prototype.slice.call(list.children);
  bar.addEventListener('click', function (ev) {
    var btn = ev.target.closest('button[data-sort]');
    if (!btn) return;
    var key = btn.dataset.sort;
    bar.querySelectorAll('button[data-sort]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b === btn));
    });
    var sorted = rows.slice().sort(function (a, b) {
      if (key === 'score') {
        /* An essay with no score sorts last rather than as a zero, which would
           put it below a genuine 0.5. */
        var sa = a.dataset.score === undefined ? -Infinity : parseFloat(a.dataset.score);
        var sb = b.dataset.score === undefined ? -Infinity : parseFloat(b.dataset.score);
        if (sb !== sa) return sb - sa;
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


def page(title, desc, body, up, here, footer):
    """`body` carries its own <h1>; the nav is injected straight after it, so the
    heading comes first and the three ways in sit under it."""
    if here and "</h1>" in body:
        head_end = body.index("</h1>") + len("</h1>") + 1
        body = body[:head_end] + nav(up, here) + body[head_end:]
    tail = TAIL.replace("FOOTER", footer)
    # Only the front page carries the sort control, so only it carries the script.
    if 'class="sortbar"' in body:
        tail = SORT_JS + tail
    return (HEAD.format(title=html.escape(title), desc=html.escape(desc), css=CSS, up=up)
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

    by_writer, by_object = {}, {}
    for e in entries:
        by_writer.setdefault(e["thinker"], []).append(e)
        by_object.setdefault(e["object"], []).append(e)

    # --- one page per essay -------------------------------------------------
    for e in entries:
        others = [x for x in by_object[e["object"]] if x is not e]
        also = ""
        if others:
            # The point of the object axis: who ELSE has been set on this thing.
            links = ", ".join(f'<a href="../e/{slug(x)}.html">{html.escape(x["name"])}</a>'
                              for x in others)
            also = f'  <p class="foot">Also on {html.escape(e["object"])}: {links}.</p>\n'
        body = ('  <a class="backlink" href="../index.html">'
                '<span class="arr">&larr;</span>&nbsp;All the essays</a>\n'
                f'  <h1 class="titled"><img class="face" src="../faces/{e["thinker"]}.jpg" '
                f'alt="" width="76" height="76" loading="lazy"><span>'
                f'<a href="../by/{e["thinker"]}.html" style="text-decoration:none">'
                f'{html.escape(e["name"])}</a> on '
                f'<a href="../on/{obj_slug(e["object"])}.html" style="text-decoration:none">'
                f'{html.escape(e["object"])}</a></span></h1>\n'
                f'  <div class="essay">\n    {paragraphs(e["essay"])}\n  </div>\n'
                + also)
        p = page(f'{e["name"]} on {e["object"]}',
                 f'A pastiche essay in the style of {e["name"]} about {e["object"]}, '
                 'which they never saw.',
                 body, "../", "", "")
        (DOCS / "e" / f"{slug(e)}.html").write_text(p, encoding="utf-8", newline="\n")

    # --- one page per writer ------------------------------------------------
    for tid, es in by_writer.items():
        name, dates = es[0]["name"], es[0]["dates"]
        body = (f'  <h1 class="titled"><img class="face" src="../faces/{tid}.jpg" alt="" '
                f'width="76" height="76" loading="lazy">'
                f'<span>{html.escape(name)}</span></h1>\n'
                f'  <ul class="list">\n{essay_rows(es, "../", show="object")}\n  </ul>\n')
        p = page(f"{name} - Ghostwriters",
                 f"Pastiche essays in the style of {name} about things that did not exist "
                 "in their lifetime.", body, "../", "writers",
                 "")
        (DOCS / "by" / f"{tid}.html").write_text(p, encoding="utf-8", newline="\n")

    # --- one page per object: everyone who has been set on it ---------------
    for obj, es in by_object.items():
        who = " and ".join([", ".join(x["name"] for x in es[:-1]), es[-1]["name"]]).strip(", ")
        # The rows are the front page's rows verbatim - name, object, verdict, score.
        body = (f'  <h1>{html.escape(obj)}</h1>\n'
                f'  <ul class="list">\n{essay_rows(es, "../")}\n  </ul>\n')
        p = page(f"{obj} - Ghostwriters",
                 f"{who} on {obj}, in pastiche.", body, "../", "objects", "")
        (DOCS / "on" / f"{obj_slug(obj)}.html").write_text(p, encoding="utf-8", newline="\n")

    # --- the three top-level views ------------------------------------------
    desc = ("We asked dead writers what they make of the modern world. "
            "They were not kind.")
    listing = f'  <ul class="list" id="all">\n{essay_rows(entries)}\n  </ul>\n' if entries else ""
    # Sorting is the only interactive thing on this page, so it is two buttons and
    # no framework. The default is the published order, newest first, which is what
    # the page has always shown and what someone arriving expects to see.
    sortbar = ('  <div class="sortbar">\n    <span>Sort</span>\n    <button type="button" data-sort="seq" aria-pressed="true">Latest</button>\n    <button type="button" data-sort="score" aria-pressed="false">Rating</button>\n  </div>\n') if entries else ""
    idx = (f'  <h1 class="wordmark">{GHOST}Ghostwriters</h1>\n'
           f'  <p class="stand">{html.escape(desc)}</p>\n' + sortbar + listing)
    (DOCS / "index.html").write_text(
        page("Ghostwriters", desc, idx, "", "index",
             ""),
        encoding="utf-8", newline="\n")

    # The whole roster, not only the writers who happen to have published. A name
    # with a nought beside it is information: it is in the rotation, not yet drawn.
    listed = ([(t["id"], t["name"], len(by_writer.get(t["id"], []))) for t in roster]
              if roster else
              [(k, v[0]["name"], len(v)) for k, v in by_writer.items()])
    chips = "\n".join(
        (f'    <li><a href="by/{tid}.html">'
         f'<img class="face" src="faces/{tid}.jpg" alt="" width="86" height="86" loading="lazy">'
         f'{html.escape(name)} <span class="n">{n}</span></a></li>') if n else
        (f'    <li><span class="chip-off">'
         f'<img class="face" src="faces/{tid}.jpg" alt="" width="86" height="86" loading="lazy">'
         f'{html.escape(name)} <span class="n">0</span></span></li>')
        for tid, name, n in sorted(listed, key=lambda x: x[1]))
    (DOCS / "writers.html").write_text(
        page("Writers - Ghostwriters",
             "Every writer in the rotation, and how many essays each has.",
             '  <h1>Writers</h1>\n'
             f'  <ul class="chips people">\n{chips}\n  </ul>\n', "", "writers",
             ""),
        encoding="utf-8", newline="\n")

    ochips = "\n".join(
        f'    <li><a href="on/{obj_slug(o)}.html">{html.escape(o)} '
        f'<span class="n">{len(es)}</span></a></li>'
        for o, es in sorted(by_object.items()))
    (DOCS / "objects.html").write_text(
        page("Subjects - Ghostwriters",
             "Every subject written about here, and how many writers have been set on it.",
             '  <h1>Subjects</h1>\n'
             f'  <ul class="chips">\n{ochips}\n  </ul>\n', "", "objects",
             ""),
        encoding="utf-8", newline="\n")
