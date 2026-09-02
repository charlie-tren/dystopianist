"""The re-read loop writes into styles/, so what it writes has to be evidence.

A critic asked "how could this be better" always answers, and answers vaguely. An Avoid
list of vague advice is worse than an empty one: it fills the prompt the writer receives
with noise that then competes with the samples for attention. So the pass only accepts a
fault that QUOTES the essay, and the quote has to really be in the essay - a critic with
nothing to say will paraphrase, and a paraphrase reads exactly like a quotation.

These are the guards on that, plus the one that stops the same fault being appended every
night until the file is nothing but repeats of itself.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("reread", ROOT / "tools" / "reread.py")
reread = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reread)

ESSAY = ("There are eleven chairs. I counted them twice, which tells you something "
         "about the kind of afternoon it was. The room was cold.")


def main() -> int:
    fails = []

    # --- a fault must carry a real quote -------------------------------------
    kept = reread.grounded(reread.parse_faults({"faults": [
        {"quote": "There are eleven chairs", "problem": "fine, this is him"},
    ]}), ESSAY)
    if len(kept) != 1:
        fails.append("a genuine quote from the essay was discarded")

    for bad, why in (
        ({"quote": "the writer counts some furniture", "problem": "x"}, "paraphrase"),
        ({"quote": "too short", "problem": "x"}, "under three words"),
        ({"quote": "There are eleven chairs", "problem": ""}, "no problem stated"),
        ({"quote": "", "problem": "vague advice with no quote"}, "no quote"),
        ("not even a dict", "malformed"),
    ):
        got = reread.grounded(reread.parse_faults({"faults": [bad]}), ESSAY)
        if got:
            fails.append(f"accepted a fault it should have dropped ({why}): {got}")

    if reread.grounded(reread.parse_faults({}), ESSAY):
        fails.append("invented faults from a response with none")

    # a quote that differs only in whitespace and case is still a quote
    ok = reread.grounded(reread.parse_faults({"faults": [
        {"quote": "THERE  ARE   ELEVEN chairs", "problem": "x"}]}), ESSAY)
    if len(ok) != 1:
        fails.append("whitespace or case difference rejected a real quote")

    # --- appending -----------------------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        real = reread.STYLES
        try:
            reread.STYLES = Path(tmp)
            (Path(tmp) / "x.md").write_text(
                "# X\n\n## Register\n\nplain\n\n## Avoid\n\n- Something already known.\n"
                "\n## Log\n\n- start\n", encoding="utf-8")
            f = [{"quote": "There are eleven chairs", "problem": "He would not count."}]
            n1 = reread.append_avoid("x", f, "2026-09-02")
            n2 = reread.append_avoid("x", f, "2026-09-03")
            body = (Path(tmp) / "x.md").read_text(encoding="utf-8")
            if n1 != 1:
                fails.append(f"first append added {n1} lines, want 1")
            if n2 != 0:
                fails.append(f"the SAME fault was appended twice ({n2}) - the file "
                             "would grow forever on a nightly job")
            if body.count("eleven chairs") != 1:
                fails.append("the fault appears more than once in the file")
            if "Something already known." not in body:
                fails.append("appending destroyed the existing Avoid list")
            if body.index("- He would not count") > body.index("## Log"):
                fails.append("the new line landed outside the Avoid section")
            # a file with no Avoid section must be left alone, not corrupted
            (Path(tmp) / "y.md").write_text("# Y\n\n## Register\n\nplain\n",
                                            encoding="utf-8")
            before = (Path(tmp) / "y.md").read_text(encoding="utf-8")
            if reread.append_avoid("y", f, "2026-09-02") != 0:
                fails.append("claimed to append to a file with no Avoid section")
            if (Path(tmp) / "y.md").read_text(encoding="utf-8") != before:
                fails.append("a file with no Avoid section was modified anyway")
        finally:
            reread.STYLES = real

    if fails:
        for f in fails:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("the re-read loop only writes faults it can quote, and writes each one once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
