"""Generate one essay: a writer, an object they never saw, in their register."""
from __future__ import annotations

import llm

# The instruction stays SHORT on purpose. The register comes from the samples, and a
# paragraph of adjectives telling the model to sound like someone loses to one example
# of them actually sounding like it.
PROMPT = """Write a short essay in the style of {name} ({dates}) about {object}, which did
not exist in their lifetime.

{samples}
What marks the voice: {note}

Rules:
- {words} words. One continuous piece, no headings, no lists.
- Take the RHYTHM from the samples: sentence length, how clauses stack, how much the
  writer qualifies. Take nothing else from them.
- Do NOT reuse a sample's opening, its phrases, or its argument. Reworking a sample's
  first sentence into one about this object is a failure, not a success. The samples
  show you how the writer moves, not what to say. Start somewhere they do not.
- Never name the author, their century, their books, or that they are dead.
- Do not define or explain {object}. Assume the reader is holding one.
- No opening throat-clearing. First sentence does work.
{avoid}
Return JSON: {{"essay": "..."}}"""


def build_prompt(thinker: dict, obj: str, words: str) -> str:
    samples = "".join(
        "A sample in that register:\n---\n" + s["text"] + "\n---\n\n"
        for s in (thinker.get("samples") or [{"text": thinker["shot"]}]))
    avoid = ""
    if thinker.get("avoid"):
        # Per-writer, so a note about Kafka is never paid for by Twain.
        lines = "\n".join("- " + a for a in thinker["avoid"])
        avoid = "\nThis writer specifically - do not:\n" + lines + "\n"
    return PROMPT.format(
        name=thinker["name"], dates=thinker["dates"], object=obj,
        samples=samples, note=thinker["note"].strip(), words=words, avoid=avoid)


def write(thinker: dict, obj: str, words: str = "170-230",
          temperature: float = 0.95) -> tuple[str, str]:
    """Returns (essay, provider). The provider is recorded with the essay so a batch
    that reads differently can be traced to the model that wrote it."""
    raw, provider = llm.generate(build_prompt(thinker, obj, words), temperature=temperature)
    essay = llm.extract_json(raw).get("essay", "")
    return " ".join(essay.split()), provider
