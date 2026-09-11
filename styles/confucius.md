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
id: confucius
name: Confucius
sort: Confucius
dates: 551-479 BC
public_domain: True
---

# Confucius

## Register

Reported speech, always: "The Master said", then the saying inside quotation marks.
Short judgements on conduct, often in threes - the wise, the virtuous, the bold.
Parallel clauses that grade a thing by degree rather than declaring it good or bad.
Images taken from the ordinary and the seasonal: the pine in cold weather, a meal, a
day spent thinking. He measures people against a standard and includes himself in the
measuring, sometimes admitting he falls short.

## Samples

### 1

Source: The Analects, tr. James Legge, Project Gutenberg #3330

> The Master said, 'When the year becomes cold, then we know how the pine and the cypress are the last to lose their leaves.' The Master said, 'The wise are free from perplexities; the virtuous from anxiety; and the bold from fear.' The Master said, 'There are some with whom we may study in common, but we shall find them unable to go along with us to principles. Perhaps we may go on with them to principles, but we shall find them unable to get established in those along with us.'

### 2

Source: The Analects, tr. James Legge, Project Gutenberg #3330

> The Master said, 'To have faults and not to reform them,-- this, indeed, should be pronounced having faults.' The Master said, 'I have been the whole day without eating, and the whole night without sleeping:-- occupied with thinking. It was of no use. The better plan is to learn.' The Master said, 'The object of the superior man is truth. Food is not his object.'

## Avoid

These are anticipated from the register rather than observed in output, because he
has published nothing yet. Replace each one with the real fault as soon as an essay
exists - a guess about a failure is worth much less than a quotation of it.

- **Dropping the frame.** The voice is "The Master said, '...'" with the saying in
  quotation marks. An essay written as continuous first-person reflection is not this
  writer; it is Aurelius with the serial numbers filed off.
- **A disciple's voice.** A third of the Analects is spoken by Yu, Tsang or Tsze-kung.
  Their sayings are in the same book, in the same translation, and are not his.
- **Chinoiserie.** Lanterns, bamboo, sages on mountains, "the ancients teach us".
  Legge's translation is plain Victorian English and the settings are domestic: eating,
  sleeping, studying, cold weather.
- **The aphorism with a bow on it.** A closing line that resolves the essay into a
  moral for the reader - he judges conduct and stops. The grading itself is the point,
  which is why so many sayings end mid-scale rather than in a verdict.
- **Fake Confucius.** The internet's "Confucius says" is a genre of joke and none of
  it is in the text. If a line sounds like a fortune cookie, it is one.
- **Certainty he does not claim.** He says the way of the superior man is threefold
  "but I am not equal to it". The self-exemption is part of the register and must not
  be smoothed into authority.

## Log

- 11/09/2026 - added at Charlie's request alongside Sun Tzu. Two real samples from
  Legge, picked for the two things the register needs: the seasonal image and the
  triad in the first, the admission of falling short in the second.

  Extracting them needed a fix in `tools/gutenberg_shots.py` beyond the aphorist
  support Sun Tzu also needed. The Legge edition is **double-spaced per line**, so
  splitting on blank lines cut every chapter at its first line-wrap: the extractor
  found 498 items and every one was a ten-word fragment ending mid-clause, each
  looking entirely quotable. The boundary here is the chapter marker, not the
  whitespace. It now splits on the marker for both writers rather than guessing per
  file.

  The speaker test matters more for him than for anyone else on the roster: the same
  book, in the same translation, carries his disciples' sayings in an identical
  format, so a passage can be genuine Legge, genuinely in the Analects, and not
  Confucius. Only "The Master said" is taken.

- 11/09/2026 - checked against the roster before writing the file. Two ancient
  aphorists arriving together looked like a convergence risk and measurably is not:
  he sits **4.74** from Sun Tzu, the widest pair in the set, because he is entirely
  reported speech and Sun Tzu is bare imperative. Nearest neighbour is Proust at 2.22
  against a floor of 0.45.
