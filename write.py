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
# Two openings and two "assume the reader" lines, because a film is not an object.
# "Which did not exist in their lifetime" is true of Jaws but says the wrong thing:
# the point is that it was RELEASED after they died, and that the writer is being
# asked for a view on a work rather than on a thing. And "has met it today" is
# nonsense about a film, where the useful instruction is that the reader has seen it.
OPENING = {
    None: "about {object}, which did not exist in their lifetime.",
    "film": ("about the film {object}, released long after their death. Write about "
             "the film itself - what happens in it, how it is made, what it wants "
             "from its audience - not about cinema in general."),
}
ASSUME = {
    None: ("Do not define or explain {object}. Assume the reader knows it and has met "
           "it today."),
    "film": ("Do not summarise the plot of {object} for someone who has not seen it. "
             "Assume the reader has, and go straight to what you make of it."),
}

# ORDER MATTERS, and this is the second thing that changed after reading the first
# fifty-eight. The samples ARE the voice; everything else is scaffolding. They used to
# sit near the top with three hundred words of rules between them and the writing, and
# the essays that came back in the model's own costume-drama register - hedged, abstract,
# no stance - were the ones where that scaffolding had drowned them out. So the register
# and the samples now come LAST, immediately before the instruction to write, and the
# writer is named again on the final line. Nothing was added; it was reordered.
PROMPT = """You are writing as {name} ({dates}).

The task: a short essay {opening}

Rules:
- {words} words. One continuous piece, no headings, no lists.
- Do not rate the object, score it, or state any number out of ten.
- Do NOT reuse a sample's opening, its phrases, or its argument. Reworking a sample's
  first sentence into one about this object is a failure, not a success. The samples
  show you how the writer moves, not what to say. Start somewhere they do not.
- Never name the author, their century, their books, or that they are dead.
- {assume} (The old wording here was "assume the reader is holding one", which
  stopped making sense the moment the list grew past gadgets: nobody holds
  anaesthesia, a hot shower or Wikipedia, and nobody holds Jaws at all.)
- No opening throat-clearing. First sentence does work. "In the vast expanse of
  human endeavour, there exists a..." is exactly the sentence not to write.
- Plain prose. No markdown, no underscores or asterisks around words for emphasis.
- Commit to a view. Admiration, contempt, ambivalence and simple attention are all
  real answers; "the notion is intriguing, though its applications are unclear" is
  not one of them. A sentence that could sit in any of these writers' mouths belongs
  in none of them.
{avoid}
HOW {upper} WRITES. This is the part to get right - the rest is housekeeping.

{note}

{samples}Take the RHYTHM from those samples: sentence length, how clauses stack, how much
the writer qualifies, where the emphasis falls. Take nothing else from them.

Now write it, as {name}, {opening_short}

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

Give a verdict of one to three words and a score as a WHOLE NUMBER from 0 to 100,
where 0 is total contempt and 100 is unreserved delight.

- Use the whole range. 41 and 58 are ordinary answers. Do not round to a multiple
  of five, and do not reach for 50 because the essay is hard to place.
- Score what THIS PROSE conveys, not what you would expect this writer to think.
- Use the ends of the scale when the essay earns them. A demolition is under 20.
  Real pleasure is over 70.
- Use the MIDDLE when the essay sits there. An essay that observes without judging,
  or accepts, or concedes a point to the thing while disliking it, is a 40, 50 or 60.
  Do not read contempt into flat attention, and do not read approval into politeness.
- The verdict is printed on the page beside the title, in the writer's company, so it
  has to sound like a phrase from the essay rather than a mark on a report. Lift the
  words from the prose where you can. "solemn humbug", "a clean limbo", "counterfeit
  suffering" are verdicts. "mild praise", "mixed feelings", "vague appreciation",
  "ambivalent observation" are grades, and are not. Never describe the essay; name
  the thing it is describing.
- Judge the STANCE, not the surface vocabulary. Calm, level or affectless prose
  about something the writer plainly finds ominous is not approval. Kafka writing
  that a device waits "quietly, patiently" for the moment to strike is describing
  dread in a flat voice, which is how he describes dread; scoring it as contentment
  because the adjectives are soft gets it exactly backwards. Ask what the piece
  would have its reader FEEL about the object, not which words it happens to use.
- Say whether the essay actually engages {object} at all. An essay that circles the
  subject without ever taking it on - describing an operating theatre and never the
  anaesthesia - is not on topic, however good the prose is.

Return JSON: {{"verdict": "...", "score": 0, "on_topic": true}}"""


# ASKED OUT OF 100, PRINTED OUT OF 10, and the difference is the whole point.
# Asked for "a score out of ten to one decimal place" the judge ignored the decimal and
# answered on the half-point grid: measured over 66 published essays, 70% landed on a .0
# or .5, which is a 21-point scale, and 66 essays into 21 buckets collides hard - nine
# essays at exactly 1.0, seven at 5.0, four at 8.5.
#
# A whole number out of 100 removes the round answer rather than arguing against it.
# A/B over six essays, same prompt otherwise: the 0-10 form put 6 of 6 on the grid and
# reproduced the live scores exactly; the 0-100 form put 0 of 5 on it and returned five
# distinct values (8, 7, 48, 47, 87). The ORDER was unchanged - demolitions stayed at the
# bottom, the liked things at the top - so this resolves finer without re-judging.
SCALE = 100


def build_prompt(thinker: dict, obj: str, words: str, kind=None) -> str:
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
        upper=thinker["name"].upper(),
        opening=OPENING.get(kind, OPENING[None]).format(object=obj),
        opening_short=("on the film " + obj + "." if kind == "film"
                       else "on " + obj + "."),
        assume=ASSUME.get(kind, ASSUME[None]).format(object=obj),
        samples=samples, note=thinker["note"].strip(), words=words, avoid=avoid)


def build_score_prompt(thinker: dict, obj: str, essay: str) -> str:
    return SCORE_PROMPT.format(name=thinker["name"], object=obj, essay=essay)


# The scoring pass is pinned to ONE model, and which one is recorded on the essay.
# Not because Gemini scores better - because a score is only meaningful against the
# other scores on the page, and two models do not share a scale. On 26/08/2026 Gemini's
# day was spent by the time the batch ran, so llama-3.3-70b scored all 22 essays while
# Gemini had scored the 17 before them. The front page ended up with a llama band at
# 5.4-5.5 and a Gemini band at 1.5-1.8, sorted against each other as though they were
# one measurement. Falling back is still allowed, because an unscorable essay fails the
# gate and a spent quota would mean no essay at all; but the fallback is RECORDED, and
# tools/rescore.py re-reads anything not scored by the canonical model once quota
# returns. Publish now, converge later.
SCORER = "gemini"


def score_essay(thinker: dict, obj: str, essay: str) -> tuple[str, float | None, bool, str]:
    """Pass two: read the finished essay and report what it expresses. Temperature is
    low because this is a reading, not a performance. Returns the scoring provider as
    well, so a corpus scored by two models is detectable rather than invisible.

    Also returns whether the essay is on topic. The reader is already here with the
    prose in front of it, so this costs nothing, and it catches a failure no string
    match can: Whitman's first anaesthesia essay described an operating theatre in
    fine detail and never once touched the anaesthetic. Absent from the gate, it
    published, and the scorer's honest verdict for it was "no mention" - which then
    printed on the site as though it were the writer's opinion."""
    raw, scored_by = llm.generate(build_score_prompt(thinker, obj, essay),
                                  temperature=0.2, prefer=SCORER)
    d = llm.extract_json(raw)
    try:
        # Out of 100 from the model, out of 10 on the page.
        #
        # NEVER guess which scale a number is on. The obvious guard - "divide by ten
        # only if it is over ten" - is a silent inverter: Orwell on airport lounges came
        # back as 8, meaning 8/100, and that rule would have published it as 8.0 out of
        # 10, turning the most contemptuous essay on the site into its warmest. The two
        # scales genuinely overlap at the bottom and no arithmetic can separate them.
        #
        # So the contract is enforced instead of inferred: a WHOLE number was asked for,
        # and anything else is a scorer that did not do as it was told. That returns None,
        # which critic.py already treats as a failed gate, so the essay is re-rolled
        # rather than published against a number nobody can interpret.
        raw_score = float(d.get("score"))
        score = round(raw_score / 10, 1) if raw_score == int(raw_score) else None
    except (TypeError, ValueError):
        score = None
    verdict = " ".join(str(d.get("verdict", "")).split()).strip(" .").lower()
    on_topic = d.get("on_topic")
    # Absent or unparseable means "do not know", and the gate should not fail an
    # essay because the scorer dropped a field.
    on_topic = True if on_topic is None else bool(on_topic)
    # The scale is part of the identity of a score, not a detail of how it was
    # produced. "gemini" alone cannot tell a 1.0 asked out of ten from a 1.0 asked
    # out of a hundred, and the archive now holds both. Recording "gemini/100"
    # makes every pre-existing entry stale automatically, so tools/rescore.py
    # drains the old scale away without anyone having to remember to reset a flag.
    return verdict, score, on_topic, f"{scored_by}/{SCALE}"


def write(thinker: dict, obj: str, words: str = "170-230",
          temperature: float = 0.95, kind=None) -> tuple[str, str, float, str, bool, str]:
    """Returns (essay, verdict, score, provider, on_topic, scored_by).

    `provider` WROTE the essay; `scored_by` READ it. They are recorded separately
    because they answer different questions: a batch that reads differently is traced
    to the model that wrote it, and a score that will not compare with its neighbours
    is traced to the model that scored it. They are usually the same model and were
    not on 26/08/2026, which is the whole reason both are kept."""
    raw, provider = llm.generate(build_prompt(thinker, obj, words, kind),
                                 temperature=temperature)
    d = llm.extract_json(raw)
    # Markdown emphasis leaks in whenever a sample carries italics - one Nietzsche
    # attempt came back with a dozen _underscored_ words, which the page would print
    # literally. It is formatting noise, not a content failure, so strip rather than
    # reject; critic.py still catches anything this misses.
    essay = re.sub(r"(?<!\w)[_*]{1,2}(?=\w)|(?<=\w)[_*]{1,2}(?!\w)", "",
                   str(d.get("essay", "")))
    essay = " ".join(essay.split())
    verdict, score, on_topic, scored_by = (score_essay(thinker, obj, essay) if essay
                                           else ("", None, False, ""))
    return essay, verdict, score, provider, on_topic, scored_by
