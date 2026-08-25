"""Generate one essay: a thinker, an object they never saw, in their register."""
from __future__ import annotations

import gemini

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
- Match the SENTENCE SHAPE of the sample, not only its opinions.
- Never name the author, their century, their books, or that they are dead.
- Do not define or explain {object}. Assume the reader is holding one.
- No opening throat-clearing. First sentence does work.

Return JSON: {{"essay": "..."}}"""


def write(thinker: dict, obj: str, words: str = "170-230", temperature: float = 0.95) -> str:
    raw = gemini.generate(PROMPT.format(
        name=thinker["name"], dates=thinker["dates"], object=obj,
        shot=thinker["shot"].strip(), note=thinker["note"].strip(), words=words,
    ), temperature=temperature)
    essay = gemini.extract_json(raw).get("essay", "")
    return " ".join(essay.split())
