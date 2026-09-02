"""Read published essays back and write what went wrong into the writer's own file.

    python tools/reread.py                 # three essays, oldest unchecked first
    python tools/reread.py --n 5           # more of them
    python tools/reread.py --writer kafka  # everything by one writer
    python tools/reread.py --dry           # show the critiques, change nothing

WHY THIS EXISTS
Every styles/*.md already carries an "Avoid" section whose documented purpose is
"failures seen in real output". Until now the only thing that put a line there was a
person reading the site and noticing. That is the loop this closes: the essays are
already written, the file that would have prevented the fault already exists, and
nothing was carrying one to the other.

WHAT IT IS NOT. It does not rewrite the essay. A published piece stays published, for
the same reason tools/rescore.py exists but no tool republishes prose: churning the
archive to chase a rubric would make the site a moving target and destroy the record of
what the generator actually did on a given day. This improves the NEXT essay by that
writer, which is where the improvement compounds.

THE CONSTRAINT THAT MAKES IT WORK. A critic asked "how could this be better" always
answers, and answers vaguely, and an Avoid list of vague advice is worse than an empty
one - it fills the prompt with noise the model then has to weigh against the samples. So
the pass must QUOTE the offending words from the essay, and a critique that quotes
nothing is discarded unread. See tests/test_reread.py, which holds it to that.

The failures found by hand on 02/09/2026, which are the shape this is looking for:
Wallace's two essays were each a single sentence with no concrete noun in them; Aurelius
narrated in the first person when his whole register is self-address. Both are specific,
both are quotable, and both belonged in a file rather than in a chat log.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import _env                        # noqa: E402
import llm                         # noqa: E402
import styles                      # noqa: E402
import write as write_stage        # noqa: E402

ESSAYS = ROOT / "data" / "essays.json"
STYLES = ROOT / "styles"

PROMPT = """You are the editor of a pastiche site. Below is a published essay that is
meant to read as {name} ({dates}), and the description of that voice the writer was
given.

THE VOICE AS SPECIFIED
{note}

{avoid_block}
THE PUBLISHED ESSAY
---
{essay}
---

Does this read as {name}, or as a generic essay wearing their name?

Report only faults you can point at. For each one, QUOTE the exact words from the essay
that are wrong and say in one line what a reader of {name} would have expected instead.
A fault you cannot quote is not a fault, and an essay with nothing quotable wrong is a
pass - say so rather than inventing something.

Do not comment on the subject matter, the opinion expressed, the length, or anything
already listed above as a known fault. Only whether the VOICE is right.

Return JSON:
{{"verdict": "pass" or "fail",
  "faults": [{{"quote": "<exact words from the essay>",
               "problem": "<one line: what is wrong and what was expected>"}}]}}"""


def parse_faults(data) -> list[dict]:
    """Faults that actually quote the essay. Everything else is discarded."""
    out = []
    for f in (data.get("faults") or []):
        if not isinstance(f, dict):
            continue
        q = str(f.get("quote", "")).strip().strip('"')
        p = " ".join(str(f.get("problem", "")).split())
        if len(q.split()) >= 3 and p:
            out.append({"quote": q, "problem": p})
    return out


def grounded(faults: list[dict], essay: str) -> list[dict]:
    """And that the quote is REALLY in the essay.

    A critic asked to quote will paraphrase when it has nothing, and a paraphrase reads
    exactly like a quotation. Normalising whitespace and case, the words have to appear.
    """
    flat = " ".join(essay.split()).lower()
    return [f for f in faults if " ".join(f["quote"].split()).lower() in flat]


def append_avoid(tid: str, faults: list[dict], today: str) -> int:
    """Add each fault to the writer's Avoid list, skipping ones already there."""
    p = STYLES / f"{tid}.md"
    s = p.read_text(encoding="utf-8")
    m = re.search(r"^## Avoid\s*$(.*?)(?=^## )", s, re.M | re.S)
    if not m:
        return 0
    existing = m.group(1)
    lines = []
    for f in faults:
        # The quote is the identity of the fault; the same one found twice is one line.
        if f["quote"][:40].lower() in existing.lower():
            continue
        lines.append(f'- {f["problem"]} Seen in a published essay: "{f["quote"]}" '
                     f'(found {today}).')
    if not lines:
        return 0
    s = s[:m.end(1)] + "\n".join(lines) + "\n" + s[m.end(1):]
    p.write_text(s, encoding="utf-8", newline="\n")
    return len(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3, help="how many essays to re-read")
    ap.add_argument("--writer", help="only this writer")
    ap.add_argument("--dry", action="store_true", help="change nothing")
    args = ap.parse_args()
    _env.load()

    entries = json.loads(ESSAYS.read_text(encoding="utf-8"))
    roster = {t["id"]: t for t in styles.load()}

    # Oldest unchecked first, so the pass works through the archive rather than
    # re-reading yesterday's essay every day and never reaching the rest.
    pool = [e for e in entries if not e.get("reread")]
    if args.writer:
        pool = [e for e in entries if e["thinker"] == args.writer]
    pool = pool[:args.n]
    print(f"{len(pool)} of {len(entries)} essays to re-read "
          f"({sum(1 for e in entries if e.get('reread'))} already checked)\n")

    added = failed = 0
    for e in pool:
        t = roster.get(e["thinker"])
        if not t:
            print(f"  ?? {e['thinker']} not in styles/, skipped")
            continue
        avoid_block = ""
        if t.get("avoid"):
            avoid_block = ("ALREADY KNOWN, do not report these again:\n"
                           + "\n".join("- " + a for a in t["avoid"]) + "\n")
        prompt = PROMPT.format(name=t["name"], dates=t["dates"], note=t["note"],
                               avoid_block=avoid_block, essay=e["essay"])
        try:
            raw, _by = llm.generate(prompt, temperature=0.2,
                                    prefer=write_stage.SCORER)
            data = llm.extract_json(raw)
        except Exception as exc:                     # noqa: BLE001
            print(f"  !! {e['thinker']}/{e['object']}: {type(exc).__name__}: {exc}"[:110])
            break
        faults = grounded(parse_faults(data), e["essay"])
        verdict = str(data.get("verdict", "")).lower()
        if verdict == "fail" and not faults:
            # Said fail, quoted nothing that is really in the essay. That is the
            # failure mode this whole tool is built around; it is not evidence.
            print(f"  -- {e['thinker']:<10} {e['object'][:24]:<24} FAIL with no usable quote")
            verdict = "unquoted"
        n = 0 if args.dry else append_avoid(e["thinker"], faults, date.today().isoformat())
        added += n
        failed += verdict == "fail"
        mark = "FAIL" if verdict == "fail" else "pass" if verdict == "pass" else verdict
        print(f"  {mark:<8} {e['thinker']:<10} {e['object'][:24]:<24} "
              f"{len(faults)} quoted fault(s), {n} new avoid line(s)")
        for f in faults:
            # Plain quotes, not curly: this prints into a CI log and a Windows console,
            # and a cp1252 console cannot decode a smart quote at all.
            print(f"           \"{f['quote'][:56]}\" -> {f['problem'][:60]}")
        if not args.dry:
            e["reread"] = date.today().isoformat()

    print(f"\n{failed} of {len(pool)} read as generic; {added} line(s) added to styles/")
    if args.dry or not pool:
        return 0
    ESSAYS.write_text(json.dumps(entries, indent=2, ensure_ascii=False),
                      encoding="utf-8", newline="\n")
    print("archive marked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
