"""Generate one essay: a writer, an object they never saw, in their register."""
from __future__ import annotations

import re

import llm

# The instruction stays SHORT on purpose. The register comes from the samples, and a
# paragraph of adjectives telling the model to sound like someone loses to one example
# of them actually sounding like it.
#
# TWO PASSES, AND THE SCORE COMES SECOND.
# It used to come first, on the reasoning that a number bolted on afterwards is
# decoration and deciding the verdict up front is what makes the two agree. They did
# agree - for the polemicists. Reading all 17 of the first batch against their scores,
# every Thompson, Nietzsche, Orwell and Twain earned its number, and seven essays did
# not: Montaigne scored 1.5 "senseless tyranny" on an essay that concedes the alarm
# clock may be "a necessary whip for a mind as sluggish as mine"; Kafka scored 1.5 on
# a narrator who "did not mind waiting"; both Didions scored under 2 for essays that
# pass no judgement at all.
#
# Asking for the verdict first was handing the writer a target before they had seen
# the thing, and a target in the register of judgement, which is a register Didion,
# Kafka, Montaigne and Aurelius do not write in. So the essay is now written with no
# number anywhere in its context, and a second pass reads the finished prose and
# scores what it actually expresses. The score became a reading rather than a brief.
PROMPT = """Write a short essay in the style of {name} ({dates}) about {object}, which did
not exist in their lifetime.

{samples}
What marks the voice: {note}

Write what this writer would actually make of it, wherever that lands. Admiration,
contempt, ambivalence and simple attention are all real answers.

Rules:
- {words} words. One continuous piece, no headings, no lists.
- Do not rate the object, score it, or state any number out of ten.
- Take the RHYTHM from the samples: sentence length, how clauses stack, how much the
  writer qualifies. Take nothing else from them.
- Do NOT reuse a sample's opening, its phrases, or its argument. Reworking a sample's
  first sentence into one about this object is a failure, not a success. The samples
  show you how the writer moves, not what to say. Start somewhere they do not.
- Never name the author, their century, their books, or that they are dead.
- Do not define or explain {object}. Assume the reader knows it and has met it
  today. (The old wording here was "assume the reader is holding one", which
  stopped making sense the moment the list grew past gadgets: nobody holds
  anaesthesia, a hot shower or Wikipedia.)
- No opening throat-clearing. First sentence does work. "In the vast expanse of
  human endeavour, there exists a..." is exactly the sentence not to write.
- Plain prose. No markdown, no underscores or asterisks around words for emphasis.
{avoid}
Return JSON: {{"essay": "..."}}"""


# Pass two. The scorer is shown the prose and nothing else about what it should think,
# and is told in as many words that a mild essay takes a mild number. The failure this
# exists to stop is an essay of level attention being filed at 1.5 because the object
# happens to be a modern annoyance.
SCORE_PROMPT = """Below is a short essay by {name} about {object}.

Read it and report what it actually expresses about {object}.

---
{essay}
---

Give a verdict of one to three words and a score out of ten to one decimal place.

- Score what THIS PROSE conveys, not what you would expect this writer to think.
- Use the ends of the scale when the essay earns them. A demolition is under 2. Real
  pleasure is over 7.
- Use the MIDDLE when the essay sits there. An essay that observes without judging,
  or accepts, or concedes a point to the thing while disliking it, is a 4, 5 or 6.
  Do not read contempt into flat attention, and do not read approval into politeness.
- The verdict must be sayable about the object and must match the number.

Return JSON: {{"verdict": "...", "score": 0.0}}"""


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


def build_score_prompt(thinker: dict, obj: str, essay: str) -> str:
    return SCORE_PROMPT.format(name=thinker["name"], object=obj, essay=essay)


def score_essay(thinker: dict, obj: str, essay: str) -> tuple[str, float | None]:
    """Pass two: read the finished essay and report what it expresses. Temperature is
    low because this is a reading, not a performance."""
    raw, _ = llm.generate(build_score_prompt(thinker, obj, essay), temperature=0.2)
    d = llm.extract_json(raw)
    try:
        score = round(float(d.get("score")), 1)
    except (TypeError, ValueError):
        score = None
    verdict = " ".join(str(d.get("verdict", "")).split()).strip(" .").lower()
    return verdict, score


def write(thinker: dict, obj: str, words: str = "170-230",
          temperature: float = 0.95) -> tuple[str, str, float, str]:
    """Returns (essay, verdict, score, provider). The provider is recorded with the
    essay so a batch that reads differently can be traced to the model that wrote it.
    It is the provider that WROTE the piece; the scoring pass may land elsewhere, and
    the prose is the thing worth tracing."""
    raw, provider = llm.generate(build_prompt(thinker, obj, words), temperature=temperature)
    d = llm.extract_json(raw)
    # Markdown emphasis leaks in whenever a sample carries italics - one Nietzsche
    # attempt came back with a dozen _underscored_ words, which the page would print
    # literally. It is formatting noise, not a content failure, so strip rather than
    # reject; critic.py still catches anything this misses.
    essay = re.sub(r"(?<!\w)[_*]{1,2}(?=\w)|(?<=\w)[_*]{1,2}(?!\w)", "",
                   str(d.get("essay", "")))
    essay = " ".join(essay.split())
    verdict, score = score_essay(thinker, obj, essay) if essay else ("", None)
    return essay, verdict, score, provider
