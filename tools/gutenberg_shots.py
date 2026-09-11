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

# --- aphorists -----------------------------------------------------------------
# THE 55-130 WORD PARAGRAPH FILTER CANNOT SEE THESE WRITERS. Sun Tzu and Confucius
# write numbered aphorisms of ten to forty words, so `paragraphs()` rejects nearly
# every line either of them ever wrote, and the handful it keeps are the longest and
# least characteristic. The unit of imitation for an aphorist is a RUN of consecutive
# aphorisms, because the rhythm between them is the voice.
#
# Both editions also carry a second voice that must be kept out, which is the
# Parkman-inside-Twain trap in a new costume and worse, because here it is plausible:
#   - Giles wraps Sun Tzu in his own bracketed commentary, often longer than the text.
#   - A third of the Analects is spoken by DISCIPLES - "The philosopher Yu said",
#     "Tsang said" - so a passage can be genuine Legge, genuinely in the book, and
#     not Confucius.
# Hence a speaker test per writer rather than a shared spread.
APHORISTS = {
    "suntzu": {
        "book": (132, "The Art of War, tr. Lionel Giles"),
        # Giles' commentary, in square brackets, and his section marks.
        "drop": [re.compile(r"\[[^\]]*\]", re.S), re.compile(r"§\s*\d+")],
        "split": r"(?=\b\d+(?:\s*,\s*\d+)*\.\s+[A-Z])",
        "item": re.compile(r"^(\d+(?:\s*,\s*\d+)*)\.\s+(.*)", re.S),
        "speaker": None,          # everything left after `drop` is Sun Tzu
    },
    "confucius": {
        "book": (3330, "The Analects, tr. James Legge"),
        "drop": [],
        # "CHAP. III. The Master said, '...'" and "CHAPTER I. 1. The Master said"
        "split": r"(?=CHAP(?:TER)?\.?\s+[IVXLC]+\.)",
        "item": re.compile(r"^CHAP(?:TER)?\.?\s+([IVXLC]+)\.\s*(?:\d+\.)?\s*(.*)",
                           re.I | re.S),
        # The Master, and nobody else. A disciple's saying is not his voice.
        "speaker": re.compile(r"^The Master (?:said|replied)", re.I),
    },
}


#: Giles' footnotes are NUMBERED paragraphs outside his brackets, so the bracket
#: filter does not catch them and they arrive looking exactly like Sun Tzu. Their
#: tell is scholarly apparatus: a cited work, a roman-numeral locus, a date in a
#: chronicle. The first candidate this extractor ever produced was one of them -
#: "See Mencius III. 1. iii. 13-20. When Wu first appears in the Ch'un Ch'iu in 584"
#: - which is the Parkman-inside-Twain fault again, and on this page it would have
#: published a Victorian sinologist's footnote as the words of Sun Tzu.
APPARATUS = re.compile(
    r"\b(See|Cf\.|ibid|op\. cit|Mencius|Ch.un Ch.iu|Tso Chuan|Shih Chi|"
    r"Chapter|commentator|text reads|literally|Giles|Ts.ao Kung|Tu Mu|Li Ch.uan)\b"
    r"|\b[IVXLC]{2,}\.\s*\d"
    r"|\b\d{3}\s*(B\.?C\.?|A\.?D\.?)\b", re.I)


ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _num(head: str, fallback: int) -> int:
    """An item's own number, arabic ("5, 6." takes the 5) or roman ("XVII").

    Needed because continuity is what makes a run readable, and the two editions
    number differently: Sun Tzu by verse, Legge by chapter in roman numerals.
    """
    head = (head or "").strip()
    if not head:
        return fallback
    first = re.split(r"\s*,\s*", head)[0]
    if first.isdigit():
        return int(first)
    total, prev = 0, 0
    for ch in reversed(first.upper()):
        v = ROMAN.get(ch)
        if v is None:
            return fallback
        total += v if v >= prev else -v
        prev = max(prev, v)
    return total or fallback


def aphorisms(text: str, spec: dict):
    """Runs of CONSECUTIVELY NUMBERED aphorisms, 55-130 words.

    Consecutive matters. Gluing whatever survived the filters produced runs that
    jumped a chapter mid-sentence and read as a shuffled deck - the rhythm between
    aphorisms IS the voice here, and a run assembled out of order misrepresents it
    while looking perfectly quotable.
    """
    for pat in spec["drop"]:
        text = pat.sub(" ", text)
    text = text.replace("_", "")
    items: list[tuple[int, str]] = []
    # SPLIT ON THE MARKER, NOT ON BLANK LINES. Legge's Analects is double-spaced per
    # line, so splitting on whitespace cut every chapter at its first wrap and
    # produced 498 ten-word fragments, each ending mid-clause and each looking like
    # a quotable aphorism. Sun Tzu's edition happens to be paragraph-spaced, but the
    # marker works for both, so there is one rule rather than a per-file guess.
    flat = " ".join(text.split())
    pieces = re.split(spec["split"], flat)
    for raw in pieces:
        line = raw.strip()
        m = spec["item"].match(line)
        if not m:
            continue
        said = m.groups()[-1].strip()
        if len(said.split()) < 6:
            continue
        if spec["speaker"] and not spec["speaker"].match(said):
            continue
        if APPARATUS.search(said):
            continue
        # The item's own number, so a run can be checked for continuity. Sun Tzu's
        # "5, 6." covers two verses at once; take the first.
        head = m.group(1) if spec["item"].groups > 1 else ""
        num = _num(head, len(items) + 1)
        items.append((num, said))

    for i in range(len(items)):
        buf, n, last = [], 0, None
        for num, said in items[i:i + 6]:
            if last is not None and num != last + 1:
                break                     # a gap: the run is not continuous prose
            buf.append(said)
            last = num
            n = len(re.findall(r"[A-Za-z']+", " ".join(buf)))
            if n >= 55:
                break
        if 55 <= n <= 130 and len(buf) > 1:
            yield n, " ".join(buf)


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

    for who, spec in APHORISTS.items():
        if only and who != only:
            continue
        book_id, title = spec["book"]
        r = S.get(f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
                  timeout=60)
        r.encoding = r.encoding or "utf-8"
        runs = list(aphorisms(body(r.text), spec))
        print(f"\n{'=' * 78}\n{who} - {title} (Gutenberg #{book_id}) - "
              f"{len(runs)} candidate runs\n{'=' * 78}")
        for i in range(6):
            n, p = runs[int(len(runs) * (0.08 + 0.16 * i))]
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
