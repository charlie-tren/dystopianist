# Drawing a portrait from a photograph

The prompt below turns a real photograph of a writer into a portrait in this site's
hand. It exists because a one-line text description is a poor proxy for a face, and
that is where the set keeps failing: Proust came back a waxed handlebar six times out
of six against a line forbidding one, Thoreau grows the moustache his line rules out,
Nietzsche needed three rounds to get flat hair, and Austen and Dickinson return smooth
and doe-eyed however hard the anti-glamour wording is pushed. A photograph settles all
of it at once, because likeness stops being something the prompt has to win an argument
about.

## What to attach

1. **The photograph of the writer.** One is enough; two or three from different angles
   is better.
2. **Two or three existing portraits from `docs/faces/`.** Use `whitman.jpg`,
   `kafka.jpg` and `didion.jpg` - deliberately unalike, an old bearded man, a young
   clean-shaven man and a woman. A model shown three similar faces copies the face;
   shown three different ones it copies the hand, which is the point.

Say which is which in the message, or the model may treat the photograph as a style
reference and the drawings as subjects.

## Check the photograph's licence first

Pre-1930 portraits are clear. Bourdain, Adams, Child, Wallace, Thompson, Didion and
Ephron are modern and their photographs are NOT automatically free - Wikimedia Commons
carries the licence for each, and "a photo exists on the internet" is not a licence.
This project already refuses to publish a misquotation as genuine; a wrongly-sourced
photograph used as a generation reference is the same problem wearing different clothes.

## The prompt

> The first image is a photograph of a real person. The others are hand-drawn ink
> caricature portraits from a single set, all by the same illustrator.
>
> Draw ONE new portrait of the person in the photograph, for that set. Match the
> drawings' line weight, cross-hatching, framing and tone exactly - it must look like
> the same hand drew it on the same afternoon.
>
> Take the LIKENESS entirely from the photograph: the shape of the head, the hairline,
> the set of the eyes, the nose, the way the mouth sits. Do not invent features, do not
> substitute a generic face, and do not soften or beautify - if the face is plain,
> gaunt or asymmetric, keep it. That is what makes it recognisable as this person and
> not as a type.
>
> A caricature, not a photorealistic render: heightened, drawn, obviously an impression
> of someone rather than a picture of them.
>
> Square. Head and shoulders. Black ink on plain white, no colour, no grey wash, no
> border, no background scene. No text, lettering, signature or watermark anywhere in
> the image.

## Afterwards

Save whatever it gives you at whatever size, uncropped and unconverted, into
`incoming/`. `tools/portraits.py` documents the processing the other portraits went
through - greyscale, a 9% inset crop, 512px, JPEG at quality 82 - and doing it in one
place is what keeps a hand-generated face byte-comparable with a generated one rather
than merely similar.

**Look for a signature before you save.** Flux inked a fake one onto Whitman's shoulder
and it survived two review passes; it sits inside the crop, so the crop will not save
you. Same for the reverse of the framing rules: a portrait that arrives with a border,
a background or a caption is a redraw, not something to trim.
