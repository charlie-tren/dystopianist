"""The renderer, which is where the silent bugs live.

Nothing in here checks that a page looks right - that needs eyes. It checks the four
things the renderer can get wrong while still producing a page that loads, which is the
shape every defect it has shipped so far has had:

  25/08/2026  a render test wrote three synthetic essay pages, the next build left them
              in place, and they went live reachable by URL
  27/08/2026  every row of a writer's page printed that writer's own name underneath,
              which is the name in the h1 directly above it, on all 18 pages

Both loaded fine. Both were found by a person reading the site, days later.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import render                      # noqa: E402
import styles                      # noqa: E402

ARCHIVE = json.loads((ROOT / "data" / "essays.json").read_text(encoding="utf-8"))


def fake(thinker="kafka", name="Franz Kafka", obj="escape rooms", score=4.2):
    return {"date": "2026-01-01", "thinker": thinker, "name": name,
            "dates": "1883-1924", "object": obj, "verdict": "voluntary sentence",
            "score": score, "essay": "One. Two. Three. Four. Five. Six. Seven. Eight."}


def rows_show_the_half_the_heading_does_not(fails):
    """A writer's page is headed by the writer, so its rows must not name them again;
    a subject page is headed by the object, so its rows must not repeat that either.
    Only the front page, headed by neither, carries both halves."""
    e = [fake()]

    writer_page = render.essay_rows(e, show="object")
    if "Franz Kafka" in writer_page:
        fails.append("writer page rows repeat the writer's name, which is the h1 above")
    if "escape rooms" not in writer_page:
        fails.append("writer page rows do not name the object")
    # The score column is deliberately absent there - a writer's own page showing a
    # column of their own marks is a chart nobody asked for. Asserted on the rendered
    # span rather than on the digits, because `data-score` is emitted on every row
    # regardless of page: it is inert anywhere the sort control is not, which is
    # everywhere but the front page, and that is fine as long as nothing prints it.
    if 'class="rate"' in writer_page or 'class="score' in writer_page:
        fails.append("writer page rows display a score")
    if 'data-score="4.2"' not in writer_page:
        fails.append("data-score stopped being emitted - the front-page sort reads it")

    front = render.essay_rows(e)
    for want in ("Franz Kafka", "escape rooms", "voluntary sentence", "4.2"):
        if want not in front:
            fails.append(f"front-page row is missing {want!r}")
    # Every row on a sortable page needs both keys or the sort silently drops it.
    if 'data-score="4.2"' not in front or 'data-seq="0"' not in front:
        fails.append("front-page row is missing data-score or data-seq")

    # An essay that never got a number must still render, without printing "None".
    noscore = render.essay_rows([fake(score=None)])
    if "None" in noscore or "data-score" in noscore:
        fails.append("an unscored essay renders a score anyway")


def slugs_are_stable_and_unique(fails):
    """Two essays colliding on a slug means one silently overwrites the other's page,
    and the archive is the only place that would show it."""
    seen = {}
    for e in ARCHIVE:
        s = render.slug(e)
        if s != render.slug(e):
            fails.append(f"slug is not stable for {e['thinker']}/{e['object']}")
        if s in seen:
            fails.append(f"slug collision: {s} used by {seen[s]} and "
                         f"{e['thinker']}/{e['object']}")
        seen[s] = f"{e['thinker']}/{e['object']}"
        if not re.fullmatch(r"[0-9a-z\-]+", s):
            fails.append(f"slug {s!r} is not url-safe")

    objs = {}
    for e in ARCHIVE:
        o = render.obj_slug(e["object"])
        if objs.setdefault(o, e["object"]) != e["object"]:
            fails.append(f"two objects share the slug {o!r}: "
                         f"{objs[o]!r} and {e['object']!r}")
    print(f"  {len(seen)} essay slugs, {len(objs)} object slugs, no collisions")


def paragraphs_never_drop_a_sentence(fails):
    """It splits one block into three-ish paragraphs. The failure worth catching is
    not an ugly split, it is a sentence that does not come out the other side."""
    for e in ARCHIVE:
        out = render.paragraphs(e["essay"])
        stripped = re.sub(r"</?p>", " ", out)
        n_in = len(e["essay"].split())
        n_out = len(re.sub(r"&[a-z]+;", "x", stripped).split())
        if n_out != n_in:
            fails.append(f"paragraphs() changed the word count for {e['thinker']}/"
                         f"{e['object']}: {n_in} in, {n_out} out")
            break
    # A very short piece is returned as one paragraph rather than split into three.
    if render.paragraphs("One. Two.").count("<p>") != 1:
        fails.append("a two-sentence essay was split anyway")
    print(f"  {len(ARCHIVE)} essays reflowed, no words lost")


def build_prunes_what_is_no_longer_real(fails):
    """The 25/08 incident: the renderer only ever ADDED, so a page from a deleted or
    renamed essay survived every rebuild and stayed reachable."""
    with tempfile.TemporaryDirectory() as tmp:
        real = render.DOCS
        try:
            render.DOCS = Path(tmp)
            roster = [{"id": "kafka", "name": "Franz Kafka"},
                      {"id": "wilde", "name": "Oscar Wilde"}]
            both = [fake(), fake("wilde", "Oscar Wilde", "dating apps", 5.5)]
            render.build(both, roster)
            pages = {p.name for p in (Path(tmp) / "e").glob("*.html")}
            if len(pages) != 2:
                fails.append(f"build wrote {len(pages)} essay pages for 2 essays")

            # Drop one and rebuild: its page must go, the other must stay.
            gone = render.slug(both[1]) + ".html"
            kept = render.slug(both[0]) + ".html"
            render.build(both[:1], roster)
            left = {p.name for p in (Path(tmp) / "e").glob("*.html")}
            if gone in left:
                fails.append(f"build left {gone} behind after its essay was removed")
            if kept not in left:
                fails.append(f"build pruned {kept}, which is still in the archive")
            # The writer with no essays keeps a chip on the roster page, greyed, not
            # a dead link - that is the point of passing the whole roster in.
            writers = (Path(tmp) / "writers.html").read_text(encoding="utf-8")
            if "chip-off" not in writers or "Oscar Wilde" not in writers:
                fails.append("a writer with no essays lost their place on the roster")
            if 'href="by/wilde.html"' in writers:
                fails.append("the roster links to a writer page that was pruned")
        finally:
            render.DOCS = real
    print("  prune keeps what is real and removes what is not")


def main() -> int:
    fails: list[str] = []
    for check in (rows_show_the_half_the_heading_does_not,
                  slugs_are_stable_and_unique,
                  paragraphs_never_drop_a_sentence,
                  build_prunes_what_is_no_longer_real):
        print(f"{check.__name__}:")
        check(fails)
    if fails:
        for f in fails:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("\nthe renderer is doing what it says")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
