# Ghostwriters

Essays by writers who died before the thing they are describing existed. Twain on
LinkedIn, Aurelius on the alarm clock, Kafka on the self-checkout machine. Each one
carries a verdict and a score out of ten, read off the finished prose.

Live at <https://charlietrenorden.com/ghostwriters/>. Renamed from "The Dystopianist"
on 25/08/2026; the old path redirects.

Pastiche, not attribution. Every essay page says so in the body, not in a footer.

## How it works

    python run.py                    # today's pairing: generate, gate, render
    python run.py --dry              # generate and gate, write nothing
    python run.py --writer kafka     # a named writer instead of the rotation
    python run.py --until 2          # backfill every writer to a minimum count
    python tests/test_voice.py
    python tools/portraits.py        # cartoon portrait per writer, free
    python tools/gutenberg_shots.py  # candidate samples from real books

One essay per run. The pairing is writer x object - 18 x 15 - and each object names the
two or three writers with a SPECIFIC reason to have an opinion on it. Those shortlisted
pairings go first, so the early essays are the strong matchups; after that it falls back
to the whole roster, because a writer meeting something they have no claim on is half
the point. Never the same pair twice, never the same writer two days running.

### The score

Two passes. The essay is written with no number anywhere in its context, then a second
call reads the finished prose and reports what it expresses. The score shows on the
front page beside the title. `critic.py` checks it exists and is in range; whether the
prose actually matches is a reading job, not a gate.

It used to be the other way round - verdict and score first, essay told to earn them -
on the reasoning that a number bolted on afterwards is decoration. Reading all 17 of
the first batch against their scores showed what that cost. Every Thompson, Nietzsche,
Orwell and Twain earned its number. Seven did not, and they were the same seven every
time: Montaigne at 1.5 "senseless tyranny" on an essay conceding the alarm clock may be
"a necessary whip for a mind as sluggish as mine"; Kafka at 1.5 on a narrator who "did
not mind waiting"; both Didions under 2 for essays that pass no judgement at all.

Asking for the verdict first handed the writer a target before they had seen the thing,
and a target in the register of judgement - which is not a register Didion, Kafka,
Montaigne or Aurelius write in. The scoring pass is now told in as many words that an
essay which observes without judging, or concedes a point while disliking something, is
a 4, 5 or 6.

The other half of the same problem was the object list. All eight of the originals were
modern irritations, so the roster was never handed anything it could like, and the first
17 essays averaged 1.8 out of ten with nothing above 4.5. Seven objects were added on
26/08/2026 that a writer could plausibly admire or genuinely split on.

## styles/ is the part that matters

One markdown file per writer, and it is the thing to improve over time:

    ## Register   how the writer moves, in a paragraph
    ## Samples    one or more, each marked as real prose (with source) or pastiche
    ## Avoid      failures seen in real output, per writer
    ## Log        dated, what changed and why

**Samples carry the imitation.** A few-shot beats an instruction, so adding a second and
third sample to a file does more for fidelity than any amount of prose in `Register`. The
`Avoid` list is per-writer on purpose: a note about Kafka should never be paid for by
Twain, which is what a shared prompt does.

### Real prose where the copyright has expired

Fourteen of the eighteen use their own words, attributed in the file: **Twain** (Life on the
Mississippi), **Wilde** (the Dorian Gray preface), **Marcus Aurelius** (Meditations,
Casaubon), **Kafka** (The Trial, Wyllie), **Nietzsche** (Beyond Good and Evil, Zimmern)
and **Montaigne** (Essays, Cotton) from Project Gutenberg, and **Orwell** (A Nice Cup of
Tea, Pleasure Spots) from Project Gutenberg **Australia** - a different site with a
different rule, life+70 rather than a US publication date, which cleared him in 2021.

Seven more joined on 26/08/2026, all from Project Gutenberg and all with two real
passages each: **Proust** (Swann's Way, Moncrieff), **Whitman** (Specimen Days),
**Austen** (Pride and Prejudice), **Woolf** (The Common Reader), **Dickens** (The
Uncommercial Traveller), **Thoreau** (Walden) and **Dickinson** (Poems, Three Series).

Where a writer has both fiction and essays the essays win, because a novel's narration
is a character doing the talking and this site wants the writer thinking aloud about
something in front of them. Dickinson is the exception and the one to watch: no prose of
hers is in the public domain, so her samples are POEMS, and her Avoid list carries an
explicit rule against verse, line breaks and rhyme.

The other four are pastiche written for this repo because they are still in copyright:
Wallace (2078), Thompson (2075), Didion (2091) and Ephron (2083). Imitating a pastiche
is a copy of a copy, and it was the likeliest reason the first batches read only broadly
like their author. Expect those four to imitate less closely, and say so rather than
pretending otherwise.

## Two providers, both free

`llm.py` tries Gemini, then Cloudflare Workers AI. Gemini's free tier is generous per
minute and stingy per DAY: on 25/08/2026 a bad gate retried three times, spent the day's
quota, and left the site empty. Cloudflare now covers that, using the credentials The
Aftertimes already needs for its illustrations.

Measured on the same Kafka prompt, so the choice is not a guess:

| Model | Time | Verdict |
|---|---|---|
| Llama 3.3 70B (default) | 5s | Holds the register |
| Mistral Small 24B | 6s | Also good; drifts toward imitating Metamorphosis |
| DeepSeek R1-distill 32B | 101s | Generic literary prose. A reasoning model; voice is not a reasoning problem |

## What this project can get wrong

**Every writer collapsing into the same voice.** Invisible on any one page - you only see
it reading two. `tests/test_voice.py` guards it at CORPUS level: sentence length, Latinate
vocabulary, person, comma density and spread across everything each writer has published,
failing if two converge, with the floor at 0.45.

Adding seven writers on 26/08/2026 compressed that space and the margin is worth
watching. The closest pair across the eighteen sample sets is now Dickens/Montaigne at
0.61, where the closest of the original eleven was Montaigne/Twain at 1.02. Still clear
of the floor, but by rather less. The gate reads the published CORPUS rather than the
samples, so this is a leading indicator rather than a failure.

**The model cloning a sample instead of imitating it.** The first batch opened Wilde with
"There is no such thing as a considerate or an inconsiderate message" - the sample's own
first line, reworked. Every Wilde essay would have started that way. The prompt now asks
for the rhythm and explicitly forbids reusing a sample's opening; the fix was checked by
measuring word overlap between each essay's first twelve words and its sample.

### What the voice test is NOT

An earlier version gated every essay on "is this fingerprint nearest its own writer's
sample". It killed a Bierce essay opening `PNEUMATIC DRYER, n.` that read as nobody but
Bierce, because long Latinate third-person sentences are Veblen's markers too, and it
burned free-tier calls doing it. It also included type-token ratio, which is
**length-dependent**, so every long essay drifted toward whichever short sample scored
lowest. Two voices being close is a fact about the writers; a corpus average catches a
real collapse, a per-essay gate mostly catches formality.

## Files

| | |
|---|---|
| `styles/*.md` | Register, samples, avoid list, log. One per writer |
| `styles.py`   | Reads them |
| `config/objects.yaml` | Things none of them saw, each with its shortlist of writers |
| `llm.py`      | Gemini, then Cloudflare. Records which one wrote each essay |
| `write.py`    | The prompt. Short - the samples do the work |
| `critic.py`   | Length, score in range, no name-drop, no year, no anachronism tells, no markdown |
| `voice.py`    | Prose fingerprints and the distance between two |
| `render.py`   | Static pages. Prunes anything the archive no longer contains |
| `run.py`      | Pick a pairing, generate, gate, retry, render |

`GEMINI_API_KEY`, `CF_ACCOUNT_ID`, `CF_API_TOKEN` in `.env` locally, or repo secrets in CI.
