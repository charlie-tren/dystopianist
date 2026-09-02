<!-- One file per writer: the voice, the samples, and what has gone wrong before.
     This is the thing to improve over time. When an essay reads wrong, the reason
     belongs in that writer's AVOID list, not in the shared prompt - a note about
     Kafka should never be paid for by Twain.

     SAMPLES carry the imitation. A few-shot beats an instruction, so adding a second
     and third sample does more for fidelity than any amount of description below.
     Where a sample has a Source line it is the writer's REAL prose; where it does
     not, it is pastiche written for this repo because the writer is still in
     copyright. Say which, always. -->

---
id: aurelius
name: Marcus Aurelius
sort: Aurelius
dates: 121-180
public_domain: True
---

# Marcus Aurelius

## Register

Second person, addressed to himself. Short admonitions, one idea each. Nature, death and proportion invoked plainly, without ornament. Never argues with anyone else - only with his own impatience.

## Samples

### 1

Source: Meditations, tr. Meric Casaubon, Project Gutenberg #2680

> What art and profession soever thou hast learned, endeavour to affect it, and comfort thyself in it; and pass the remainder of thy life as one who from his whole heart commits himself and whatsoever belongs unto him, unto the gods: and as for men, carry not thyself either tyrannically or servilely towards any.

## Avoid

- Naming Rome, gods, or emperors. The register is the point, not the setting.
- Consoling the reader. He is talking to himself and does not know anyone is listening.
- **First person reporting an experience.** "As I lie here, a device screams at me" and "As I find myself confined in a room" are both published, and both get the grammar backwards: he addresses HIMSELF in the second person - "thou hast", "carry not thyself" - about a general condition, rather than narrating something that just happened to him. He is not a witness filing a report.
- **Ornament.** "In the grand tapestry of existence", "the impermanence of all things", "the journey" - the register says plainly and without ornament, and these are the opposite: greeting-card stoicism, which is what the model reaches for when it knows the brand and not the voice. Nature, death and proportion get named flatly or not at all.
- **The consoling last line.** "It is not the escape that matters, but the journey" is a fortune cookie. He ends on the admonition, not on a moral offered to somebody else.
- Long compound sentences carrying three ideas. One idea each, and stop.

## Log

- 02/09/2026 - Avoid list rewritten from the two published essays, both by the fallback
  model. The Register was already right and specific; the output simply ignored it, so
  the failures are now named in the writer's own file where the prompt will carry them.
  He still has ONE sample against a 24-writer average of two, and he is public domain,
  so a second real passage should be pulled with tools/gutenberg_shots.py rather than
  written - inventing a Meditations quotation is the one thing this repo refuses.

- 25/08/2026 - migrated from config/thinkers.yaml; Avoid list seeded from the first batch.
