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
.tabs{display:flex;gap:1.5rem;margin:0 0 2rem;font:600 12px/1 var(--sans);
  letter-spacing:.14em;text-transform:uppercase}
.tabs a{color:var(--faint);text-decoration:none;padding-bottom:.4rem;border-bottom:2px solid transparent}
.tabs a:hover{color:var(--ink)}
.tabs a[aria-current]{color:var(--ink);border-bottom-color:var(--accent)}
.chips{display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 2.4rem;padding:0;list-style:none}
.chips a{display:inline-block;text-decoration:none;border:1px solid var(--rule);
  border-radius:999px;padding:.42rem .8rem;font:500 13px/1 var(--sans);color:var(--dim)}
.chips a:hover{color:var(--ink);border-color:var(--accent)}
.chips .n{color:var(--faint);font-size:11.5px}
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


def nav(up: str, here: str) -> str:
    """Three ways in: newest first, by writer, by object. Rendered on every page so
    the site is browsable from wherever you land, not only from the front page."""
    items = [("index", "Latest", f"{up}index.html"),
             ("writers", "By writer", f"{up}writers.html"),
             ("objects", "By object", f"{up}objects.html")]
    out = ['  <nav class="tabs">']
    for key, label, href in items:
        cur = ' aria-current="page"' if key == here else ""
        out.append(f'<a href="{href}"{cur}>{label}</a>')
    out.append("</nav>")
    return "".join(out) + "\n"


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


def obj_slug(obj: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in obj.lower()).strip("-")[:50]


def essay_rows(entries, up="", show="both") -> str:
    """A list of essays. `show` drops whichever half is already the page's heading -
    on a writer's page every row says the same name, and on an object's page every
    row says the same object."""
    rows = []
    for e in reversed(entries):
        if show == "object":
            t = html.escape(e["object"])
        elif show == "writer":
            t = html.escape(e["name"])
        else:
            t = f'{html.escape(e["name"])} on {html.escape(e["object"])}'
        rows.append(
            f'    <li><a href="{up}e/{slug(e)}.html">'
            f'<span class="t">{t}</span>'
            f'<span class="sub">{html.escape(e["dates"])} &middot; {e["date"]}</span></a></li>')
    return "\n".join(rows)


def page(title, desc, body, up, here, footer):
    return (HEAD.format(title=html.escape(title), desc=html.escape(desc), css=CSS, up=up)
            + nav(up, here) + body + TAIL.replace("FOOTER", footer))


def build(entries: list[dict]) -> None:
    DOCS.mkdir(exist_ok=True)
    for sub in ("e", "by", "on"):
        (DOCS / sub).mkdir(exist_ok=True)

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
            also = (f'  <p class="foot">Also on {html.escape(e["object"])}: {links}. '
                    f'<a href="../on/{obj_slug(e["object"])}.html">All of them</a>.</p>\n')
        body = ('  <p class="eyebrow">In the style of</p>\n'
                f'  <h1><a href="../by/{e["thinker"]}.html" style="text-decoration:none">'
                f'{html.escape(e["name"])}</a> on '
                f'<a href="../on/{obj_slug(e["object"])}.html" style="text-decoration:none">'
                f'{html.escape(e["object"])}</a></h1>\n'
                f'  <p class="stand">{html.escape(e["dates"])} &middot; written {e["date"]}</p>\n'
                f'  <div class="essay">\n    {paragraphs(e["essay"])}\n  </div>\n'
                f'  {pastiche_note(e["name"], e["dates"], e["object"])}\n' + also)
        p = page(f'{e["name"]} on {e["object"]}',
                 f'A pastiche essay in the style of {e["name"]} about {e["object"]}, '
                 'which they never saw.',
                 body, "../", "", '<a href="../index.html">All the essays</a>')
        (DOCS / "e" / f"{slug(e)}.html").write_text(p, encoding="utf-8", newline="\n")

    # --- one page per writer ------------------------------------------------
    for tid, es in by_writer.items():
        name, dates = es[0]["name"], es[0]["dates"]
        body = (f'  <p class="eyebrow">In the style of</p>\n  <h1>{html.escape(name)}</h1>\n'
                f'  <p class="stand">{html.escape(dates)} &middot; {len(es)} '
                f'{"essay" if len(es) == 1 else "essays"} on things they never saw.</p>\n'
                f'  <ul class="list">\n{essay_rows(es, "../", show="object")}\n  </ul>\n')
        p = page(f"{name} - The Dystopianist",
                 f"Pastiche essays in the style of {name} about things that did not exist "
                 "in their lifetime.", body, "../", "writers",
                 '<a href="../writers.html">All the writers</a>')
        (DOCS / "by" / f"{tid}.html").write_text(p, encoding="utf-8", newline="\n")

    # --- one page per object: everyone who has been set on it ---------------
    for obj, es in by_object.items():
        who = " and ".join([", ".join(x["name"] for x in es[:-1]), es[-1]["name"]]).strip(", ")
        body = (f'  <p class="eyebrow">On</p>\n  <h1>{html.escape(obj)}</h1>\n'
                f'  <p class="stand">{len(es)} '
                f'{"writer" if len(es) == 1 else "writers"} on it, none of whom saw one.</p>\n'
                f'  <ul class="list">\n{essay_rows(es, "../", show="writer")}\n  </ul>\n')
        p = page(f"{obj} - The Dystopianist",
                 f"{who} on {obj}, in pastiche.", body, "../", "objects",
                 '<a href="../objects.html">Every object</a>')
        (DOCS / "on" / f"{obj_slug(obj)}.html").write_text(p, encoding="utf-8", newline="\n")

    # --- the three top-level views ------------------------------------------
    desc = ("Essays by writers who died before the thing they are describing existed. "
            "Pastiche, written by a language model in imitation of their style.")
    idx = ('  <h1>The Dystopianist</h1>\n'
           f'  <p class="stand">{html.escape(desc)}</p>\n'
           f'  <ul class="list">\n{essay_rows(entries)}\n  </ul>\n')
    (DOCS / "index.html").write_text(
        page("The Dystopianist", desc, idx, "", "index",
             f"{len(entries)} essays. Nothing here is a quotation."),
        encoding="utf-8", newline="\n")

    chips = "\n".join(
        f'    <li><a href="by/{tid}.html">{html.escape(es[0]["name"])} '
        f'<span class="n">{len(es)}</span></a></li>'
        for tid, es in sorted(by_writer.items(), key=lambda kv: kv[1][0]["name"]))
    (DOCS / "writers.html").write_text(
        page("By writer - The Dystopianist",
             "Every writer with an essay here, and how many they have.",
             '  <h1>By writer</h1>\n  <p class="stand">Pick a voice.</p>\n'
             f'  <ul class="chips">\n{chips}\n  </ul>\n', "", "writers",
             f"{len(by_writer)} writers."),
        encoding="utf-8", newline="\n")

    ochips = "\n".join(
        f'    <li><a href="on/{obj_slug(o)}.html">{html.escape(o)} '
        f'<span class="n">{len(es)}</span></a></li>'
        for o, es in sorted(by_object.items()))
    (DOCS / "objects.html").write_text(
        page("By object - The Dystopianist",
             "Every object written about here, and how many writers have been set on it.",
             '  <h1>By object</h1>\n'
             '  <p class="stand">Pick a thing. The number is how many writers have been '
             'set on it.</p>\n'
             f'  <ul class="chips">\n{ochips}\n  </ul>\n', "", "objects",
             f"{len(by_object)} objects."),
        encoding="utf-8", newline="\n")
