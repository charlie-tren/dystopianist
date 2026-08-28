"""Read the per-writer style files in styles/.

One file per writer is the point: a note about Kafka should never be paid for by
Twain, and a shared prompt makes everyone pay for everyone. Each file carries the
register, one or more samples, and a list of things that have gone wrong before -
and that last list is what improves over time, because it is written from real
output rather than from imagination.

The format is markdown with YAML front matter so the files stay readable and
diffable on their own. Sections:

    ## Register   one paragraph on how the writer moves
    ## Samples    "### n", an optional "Source:" line, then a "> " quoted passage
    ## Avoid      "- " bullets, each a failure seen in real output
    ## Log        "- " bullets, dated, what changed and why

A sample with a Source line is the writer's real prose. Without one it is pastiche
written for this repo, because the writer is still in copyright. That distinction
is carried through to the site, so nothing implies a quotation that is not one.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
STYLES = ROOT / "styles"


def _section(body: str, name: str) -> str:
    m = re.search(rf"^##\s+{name}\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.S)
    return m.group(1).strip() if m else ""


def _bullets(text: str) -> list[str]:
    return [re.sub(r"^-\s*", "", l).strip()
            for l in text.splitlines() if l.strip().startswith("- ")]


def parse(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    m = re.search(r"^---\s*$(.*?)^---\s*$(.*)", raw, re.M | re.S)
    if not m:
        raise ValueError(f"{path.name}: no front matter")
    meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)

    samples = []
    for block in re.split(r"^###\s+\d+\s*$", _section(body, "Samples"), flags=re.M)[1:]:
        src = re.search(r"^Source:\s*(.+)$", block, re.M)
        quote = " ".join(re.sub(r"^>\s?", "", l) for l in block.splitlines()
                         if l.strip().startswith(">"))
        if quote.strip():
            source = (src.group(1).strip() if src else "")
            samples.append({"text": " ".join(quote.split()),
                            # "pastiche" in the source line means it is not a quotation
                            "source": "" if "pastiche" in source.lower() else source})
    if not samples:
        raise ValueError(f"{path.name}: no samples")

    return {**meta,
            "note": " ".join(_section(body, "Register").split()),
            "samples": samples,
            "avoid": _bullets(_section(body, "Avoid")),
            # kept so older callers that expect a single sample still work
            "shot": samples[0]["text"],
            "shot_source": samples[0]["source"]}


def load() -> list[dict]:
    """Writers, in the order a ROSTER wants them: by the name a reader holds them by.

    `sort:` in the front matter, and it is stated per writer rather than derived from
    the display name, because the last word is wrong three times out of twenty-three.
    Marcus Aurelius files under Aurelius, which is not a surname at all. Michel de
    Montaigne files under Montaigne, dropping the particle. David Foster Wallace files
    under Wallace, not Foster. A clever rule would get all three wrong quietly; a
    stated key is checked by tests/test_roster.py and cannot.

    Nobody thinks "Eric Blair" or even reaches for "George" - they think Orwell,
    Kafka, Didion, Proust. First-name order also put David Foster Wallace next to
    Douglas Adams, which is an adjacency that helps no one.
    """
    out = [parse(p) for p in sorted(STYLES.glob("*.md"))]
    ids = [t["id"] for t in out]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate writer id in styles/")
    missing = [t["id"] for t in out if not str(t.get("sort", "")).strip()]
    if missing:
        raise ValueError("no sort: key in styles/ for " + ", ".join(missing))
    out.sort(key=lambda t: (t["sort"].lower(), t["name"].lower()))
    return out


if __name__ == "__main__":
    for t in load():
        real = sum(1 for s in t["samples"] if s["source"])
        print(f"{t['id']:10} {len(t['samples'])} sample(s) ({real} real) "
              f"| {len(t['avoid'])} avoid | {t['name']}")
