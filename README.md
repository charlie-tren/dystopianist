# The Dystopianist

Essays by writers who died before the thing they are describing existed. Diogenes on
the self-checkout machine, Orwell on the smart fridge, Dorothy Parker on the
productivity app.

Live at <https://charlietrenorden.com/dystopianist/>.

Pastiche, not attribution. Every page says so in the body, not in a footer.

## How it works

    python run.py          # today's pairing: generate, gate, render
    python run.py --dry    # generate and gate, write nothing
    python tests/test_voice.py

One essay per run. The pairing is thinker x object: 8 x 40 = 320 combinations, never
the same pair twice and never the same thinker two days running, so it does not repeat
itself for most of a year.

## The one thing this project can get wrong

**Every thinker collapsing into the same voice.** An LLM's default "cynic" is a single
narrow register, and the failure is invisible on any one page - you only see it reading
two.

The fix is per-thinker few-shots, in `config/thinkers.yaml`. Each thinker carries its
own sample of its own prose, because a few-shot beats an instruction: one example of a
voice does more than a paragraph of adjectives asking for one. Adding a thinker means
writing a sample, not extending a prompt.

**Every sample in that file is pastiche written for this repo. None is a real
quotation.** Several of these writers are still in copyright, and a real excerpt in a
public repo is a reproduction. It also keeps each sample tuned to the sentence SHAPE
the generator should copy.

`tests/test_voice.py` guards the balance at corpus level: it measures sentence length,
Latinate vocabulary, person, comma density and spread for everything each thinker has
published, and fails if two of them converge. The eight reference samples sit at 0.88
for their closest pair (Debord and Veblen, fairly - both abstract and Latinate), so the
floor is 0.45.

### What that test is NOT

The first version gated every essay on "does this fingerprint sit nearer its own
thinker's sample than anyone else's". It was wrong and it is worth knowing why, because
it looked reasonable:

- It killed a Bierce essay opening `PNEUMATIC DRYER, n.` that reads as nobody but
  Bierce, because long Latinate third-person sentences are also Veblen's markers.
- Three Debord attempts died the same way, burning free-tier calls to reject good work.
- The metric originally included type-token ratio, which is **length-dependent** - a
  45-word sample scores ~0.8 and a 190-word essay ~0.70 whatever the voice - so every
  essay drifted toward whichever sample had the lowest TTR.

Two voices being close is a fact about the writers. A corpus-level average catches a
real collapse; a per-essay gate mostly catches formality.

## Files

| | |
|---|---|
| `config/thinkers.yaml` | Who, and one sample of each voice. The whole mechanism |
| `config/objects.yaml`  | Things none of them saw |
| `write.py`   | The prompt. Deliberately short - the sample does the work |
| `critic.py`  | Deterministic gates: length, no name-drop, no year, no anachronism tells |
| `voice.py`   | Prose fingerprints and the distance between two |
| `render.py`  | Static pages, no build step, no framework |
| `run.py`     | Pick a pairing, generate, gate, retry, render |

`GEMINI_API_KEY` in `.env` locally, or a repo secret in CI. Free tier, one essay a day.
