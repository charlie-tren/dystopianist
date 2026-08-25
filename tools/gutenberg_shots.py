"""Pull candidate voice samples from Project Gutenberg.

The samples in config/thinkers.yaml were pastiche I wrote, which means the model was
imitating an imitation - the likeliest reason the essays read only broadly like their
author. For writers whose copyright has expired, the real prose is free, keyless and
verifiable, so it should be the sample instead.

    python tools/gutenberg_shots.py            # print candidates to choose from

It PRINTS candidates rather than writing the config: which paragraph best shows a
voice is a judgement, and picking automatically would put an unread passage in front
of the model and on the site.

Not every writer is available. Orwell died in 1950 and is NOT on Gutenberg - anything
post-1929 is still in US copyright - so he keeps a pastiche sample and is marked as
such in the config.
"""
from __future__ import annotations

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
}

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


def main(only=None) -> int:
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
