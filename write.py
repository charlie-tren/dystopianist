"""Generate one essay: a thinker, an object they never saw, in their register."""
from __future__ import annotations

import llm

# The instruction stays SHORT on purpose. The register comes from the shot, and a
# paragraph of adjectives telling the model to sound like someone loses to one
# example of them actually sounding like it.
PROMPT = """Write a short essay in the style of {name} ({dates}) about {object}, which did
not exist in their lifetime.

A sample in that register:
---
{shot}
---
What marks the voice: {note}

Rules:
- {words} words. One continuous piece, no headings, no lists.
- Take the RHYTHM from the sample: sentence length, how clauses stack, how much the
  writer qualifies. Take nothing else from it.
- Do NOT reuse the sample's opening, its phrases, or its argument. Reworking
  "There is no such thing as a moral or an immoral book" into a sentence about this
  object is a failure, not a success. The sample shows you how the writer moves, not
  what to say. Start somewhere the sample does not.
- Never name the author, their century, their books, or that they are dead.
- Do not define or explain {object}. Assume the reader is holding one.
- No opening throat-clearing. First sentence does work.

Return JSON: {{"essay": "..."}}"""


def write(thinker: dict, obj: str, words: str = "170-230",
          temperature: float = 0.95) -> tuple[str, str]:
    """Returns (essay, provider). The provider is recorded with the essay so a batch
    that reads differently can be traced to the model that wrote it."""
    raw, provider = llm.generate(PROMPT.format(
        name=thinker["name"], dates=thinker["dates"], object=obj,
        shot=thinker["shot"].strip(), note=thinker["note"].strip(), words=words,
    ), temperature=temperature)
    essay = llm.extract_json(raw).get("essay", "")
    return " ".join(essay.split()), provider
