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
  --rule:#2C2724;--accent:#B98A4A;
  --body:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
:root[data-theme="light"]{--ground:#F3F0EA;--panel:#FBF9F5;--ink:#1B1815;--dim:#5A5349;
  --faint:#8A8175;--rule:#DCD5C9;--accent:#8A5A1E}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ground);color:var(--ink);font:400 18px/1.68 var(--body)}
a{color:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.wrap{max-width:660px;margin:0 auto;padding:2.2rem 1.4rem 5rem}
.bar{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:3.4rem}
.home{order:2;font:500 13px/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;
  color:var(--dim);text-decoration:none;display:inline-flex;align-items:center;gap:0}
.home:hover{color:var(--accent)}
.home .back{color:var(--accent);font-size:14px}
.tog{order:1;appearance:none;cursor:pointer;background:transparent;color:var(--dim);
  border:1px solid var(--rule);border-radius:999px;padding:.42rem .8rem;
  font:500 12px/1 var(--sans);letter-spacing:.04em}
.tog:hover{color:var(--ink);border-color:var(--accent)}
h1{font-weight:400;font-size:clamp(2rem,5.5vw,2.9rem);line-height:1.1;margin:0 0 .5rem;
  letter-spacing:-.01em;text-wrap:balance}
.stand{color:var(--dim);font-size:1.08rem;margin:0 0 2.6rem;max-width:46ch}
.eyebrow{font:600 11px/1 var(--sans);letter-spacing:.22em;text-transform:uppercase;
  color:var(--accent);margin:0 0 1.1rem}
.essay p{margin:0 0 1.35rem}
.essay p:first-of-type::first-letter{float:left;font-size:3.4rem;line-height:.86;
  padding:.06em .09em 0 0;color:var(--accent)}
.pastiche{margin:3rem 0 0;padding:1rem 1.1rem;border:1px solid var(--rule);border-radius:6px;
  background:var(--panel);color:var(--dim);font:400 14px/1.6 var(--sans)}
.pastiche b{color:var(--ink);font-weight:600}
.list{list-style:none;margin:0;padding:0}
.list li{border-top:1px solid var(--rule);padding:1.1rem 0}
.list li:last-child{border-bottom:1px solid var(--rule)}
.list a{text-decoration:none;display:block}
.list a:hover .t{color:var(--accent)}
.t{font-size:1.28rem}
.sub{color:var(--faint);font:400 13.5px/1.5 var(--sans);margin-top:.2rem}
.foot{margin-top:3.4rem;color:var(--faint);font:400 13px/1.6 var(--sans)}
.foot a{color:var(--dim)}
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


def pastiche_note(name: str, dates: str, obj: str) -> str:
    """Said on EVERY essay page, in the body, not in a footer. These are real
    people and the essay puts words in their mouths; a disclaimer nobody scrolls
    to is not a disclaimer."""
    return ('<p class="pastiche"><b>This is pastiche.</b> '
            f'{html.escape(name)} ({html.escape(dates)}) never wrote a word about '
            f'{html.escape(obj)} and never saw one. It is written in imitation of their '
            'style by a language model, the way a cartoonist draws a likeness. '
            'Nothing here is a quotation.</p>')


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


def build(entries: list[dict]) -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "e").mkdir(exist_ok=True)

    for e in entries:
        title = f'{e["name"]} on {e["object"]}'
        desc = (f'A pastiche essay in the style of {e["name"]} about {e["object"]}, '
                'which they never saw.')
        page = (HEAD.format(title=html.escape(title), desc=html.escape(desc), css=CSS, up="../")
                + '  <p class="eyebrow">In the style of</p>\n'
                + f'  <h1>{html.escape(e["name"])} on {html.escape(e["object"])}</h1>\n'
                + f'  <p class="stand">{html.escape(e["dates"])} &middot; written {e["date"]}</p>\n'
                + f'  <div class="essay">\n    {paragraphs(e["essay"])}\n  </div>\n'
                + f'  {pastiche_note(e["name"], e["dates"], e["object"])}\n'
                + TAIL.replace("FOOTER", '<a href="../">All the essays</a>'))
        (DOCS / "e" / f"{slug(e)}.html").write_text(page, encoding="utf-8", newline="\n")

    items = "\n".join(
        f'    <li><a href="e/{slug(e)}.html">'
        f'<span class="t">{html.escape(e["name"])} on {html.escape(e["object"])}</span>'
        f'<span class="sub">{html.escape(e["dates"])} &middot; {e["date"]}</span></a></li>'
        for e in reversed(entries))
    desc = ("Essays by writers who died before the thing they are describing existed. "
            "Pastiche, written by a language model in imitation of their style.")
    index = (HEAD.format(title="The Dystopianist", desc=html.escape(desc), css=CSS, up="")
             + '  <h1>The Dystopianist</h1>\n'
             + f'  <p class="stand">{html.escape(desc)}</p>\n'
             + f'  <ul class="list">\n{items}\n  </ul>\n'
             + TAIL.replace("FOOTER", f"{len(entries)} essays. Nothing here is a quotation."))
    (DOCS / "index.html").write_text(index, encoding="utf-8", newline="\n")
