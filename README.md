# Ghostwriters

Essays by writers who died before the thing they are describing existed. Twain on the
karaoke machine, Orwell on the doorbell camera, Kafka on the unsubscribe flow.

Live at <https://charlietrenorden.com/ghostwriters/>. Renamed from "The Dystopianist"
on 25/08/2026; the old path redirects.

Pastiche, not attribution. Every essay page says so in the body, not in a footer.

## How it works

    python run.py          # today's pairing: generate, gate, render
    python run.py --dry    # generate and gate, write nothing
    python tests/test_voice.py
    python tools/portraits.py        # cartoon portrait per writer, free
    python tools/gutenberg_shots.py  # candidate samples from real books

One essay per run. The pairing is writer x object: 8 x 35 = 280 combinations, never the
same pair twice and never the same writer two days running.

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

Five writers use their own words, attributed in the file: **Twain** (Life on the
Mississippi), **Wilde** (the Dorian Gray preface), **Marcus Aurelius** (Meditations,
Casaubon) and **Kafka** (The Trial, Wyllie) from Project Gutenberg, and **Orwell**
(A Nice Cup of Tea, Pleasure Spots) from Project Gutenberg **Australia** - a different
site with a different rule, life+70 rather than a US publication date, which cleared
him in 2021. The remaining three are pastiche written for this repo because they are
still in copyright: Wallace (2078), Thompson (2075) and Didion (2091).

Imitating a pastiche is a copy of a copy, and it was the likeliest reason the first
batches read only broadly like their author. Expect those three to imitate less
closely, and say so rather than pretending otherwise.

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
failing if two converge. The eight samples sit at 0.61 for their closest pair, so the floor
is 0.45.

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
| `config/objects.yaml` | Things none of them saw |
| `llm.py`      | Gemini, then Cloudflare. Records which one wrote each essay |
| `write.py`    | The prompt. Short - the samples do the work |
| `critic.py`   | Length, no name-drop, no year, no anachronism tells |
| `voice.py`    | Prose fingerprints and the distance between two |
| `render.py`   | Static pages. Prunes anything the archive no longer contains |
| `run.py`      | Pick a pairing, generate, gate, retry, render |

`GEMINI_API_KEY`, `CF_ACCOUNT_ID`, `CF_API_TOKEN` in `.env` locally, or repo secrets in CI.
