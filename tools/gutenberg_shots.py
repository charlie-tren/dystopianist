"""Pull candidate voice samples from Project Gutenberg.

The samples in config/thinkers.yaml were pastiche I wrote, which means the model was
imitating an imitation - the likeliest reason the essays read only broadly like their
author. For writers whose copyright has expired, the real prose is free, keyless and
verifiable, so it should be the sample instead.

    python tools/gutenberg_shots.py            # print candidates to choose from

It PRINTS candidates rather than writing the config: which paragraph best shows a
voice is a judgement, and picking automatically would put an unread passage in front
of the model and on the site.

Not every writer is available. Gutenberg proper stops at 1929, so Orwell is not there -
but Project Gutenberg AUSTRALIA runs on life+70, which put him in the public domain in
2021, and that is where his samples come from. Wallace, Thompson and Didion have no
free source and keep pastiche samples, marked as such in styles/.
"""
from __future__ import annotations

import html
import re
import sys

import requests

S = requests.Session()
S.headers["User-Agent"] = "ghostwriters/1.0 (personal project)"

# id -> (writer, title). Chosen for register, not fame: the Dorian Gray preface is
# pure epigram, Life on the Mississippi is Twain thinking aloud rather than in
# character, and The Trial is Wyllie's public-domain translation.
BOOKS = {
    "twain":    (245, "Life on the Mississippi"),
    "wilde":    (174, "The Picture of Dorian Gray"),
    "aurelius": (2680, "Meditations"),
    "kafka":    (7849, "The Trial"),
    # Added 26/08/2026. Where a writer has both fiction and essays, the essays win:
    # a novel's narration is a character doing the talking, and this site wants the
    # writer thinking aloud about a thing in front of them.
    "proust":    (7178, "Swann's Way (Moncrieff)"),
    "whitman":   (8813, "Specimen Days"),
    "austen":    (1342, "Pride and Prejudice"),
    "woolf":     (64457, "The Common Reader"),
    "dickinson": (12242, "Poems, Three Series"),
    "dickens":   (914, "The Uncommercial Traveller"),
    "thoreau":   (205, "Walden"),
    # Added 28/08/2026. Franklin's Autobiography is him explaining a practical scheme
    # and grading himself on it, which is the register the site wants; What Is Art? is
    # late Tolstoy judging a cultural product outright, rather than narrating a character.
    "franklin":  (20203, "The Autobiography of Benjamin Franklin"),
    "tolstoy":   (64908, "What Is Art?"),
}

# A NOVELIST IS NOT AN ESSAYIST, and sampling at 25-70% through the book cannot tell
# the difference. That spread is right for Walden, Specimen Days and The Uncommercial
# Traveller, where any page is the writer thinking aloud. It fails for Wilde: every
# candidate it returns from Dorian Gray is third-person narration, and his essayistic
# register - the epigram - is in the PREFACE, which the spread skips. Kafka survives
# the same treatment only because his narration IS his voice.
# So when adding a fiction-only writer here, read the candidates against what the site
# actually asks for (a view on an object) before taking one. Wilde was left on a single
# sample on 02/09/2026 for exactly this reason: no second sample beats a wrong one.
# Project Gutenberg Australia, which is a different site with a different rule:
# life + 70 rather than a US publication date. Orwell cleared there in 2021.
AU = {"orwell": ("http://gutenberg.net.au/ebooks03/0300011h.html", "Fifty Orwell Essays")}

START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.S)
END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG", re.S)


def body(text: str) -> str:
    m = START.search(text)
    if m:
        text = text[m.end():]
    m = END.search(text)
    if m:
        text = text[:m.start()]
    return text


def paragraphs(text: str):
    for raw in re.split(r"\n\s*\n", text):
        p = " ".join(raw.split())
        if not p or p.isupper():
            continue
        if re.match(r"^(chapter|part|book|section|[IVXL]+\.?$)", p, re.I):
            continue
        words = len(re.findall(r"[A-Za-z']+", p))
        if not 55 <= words <= 130:
            continue
        if p.count('"') > 2 or p.count("_") > 4:      # dialogue-heavy or italics markup
            continue
        # A paragraph opening with a quote mark is usually the author quoting
        # SOMEONE ELSE - the first Twain candidate this script produced was a slab
        # of Parkman sitting inside Life on the Mississippi. Wrong voice entirely.
        if p[0] in "'‘“\"":
            continue
        yield words, p


def strip_html(raw: str) -> str:
    """PG Australia serves HTML, not the plain text Gutenberg proper offers. Keep the
    paragraph breaks the tags carry, then hand the result to the same filter."""
    raw = re.sub(r"(?is)<(script|style|head).*?</\1>", "", raw)
    raw = re.sub(r"(?i)</p>|<br\s*/?>|</h\d>", "\n\n", raw)
    return html.unescape(re.sub(r"<[^>]+>", "", raw))


def main(only=None) -> int:
    for who, (url, title) in AU.items():
        if only and who != only:
            continue
        r = S.get(url, timeout=60)
        r.encoding = r.encoding or "utf-8"
        paras = list(paragraphs(strip_html(r.text)))
        print(f"\n{'=' * 78}\n{who} - {title} (PG Australia) - {len(paras)} candidates\n{'=' * 78}")
        for i in range(4):
            n, p = paras[int(len(paras) * (0.25 + 0.15 * i))]
            print(f"\n[{i}] {n} words\n{p}")

    for who, (book_id, title) in BOOKS.items():
        if only and who != only:
            continue
        url = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
        r = S.get(url, timeout=60)
        if r.status_code != 200:
            url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
            r = S.get(url, timeout=60)
        r.encoding = r.encoding or "utf-8"
        paras = list(paragraphs(body(r.text)))
        print(f"\n{'=' * 78}\n{who} - {title} (Gutenberg #{book_id}) - {len(paras)} candidates\n{'=' * 78}")
        # spread the sample across the book: openings are throat-clearing, ends are plot
        for i in range(4):
            n, p = paras[int(len(paras) * (0.25 + 0.15 * i))]
            print(f"\n[{i}] {n} words\n{p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
