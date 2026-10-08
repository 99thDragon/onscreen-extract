# Reading frames that fight back

Notes for cases where the straightforward pass does not get you there.

## Characters that look alike

In compressed video at small sizes these pairs are genuinely ambiguous, and
guessing wrong produces a URL that looks right and goes nowhere:

| Confusable | How to settle it |
|---|---|
| `l` `1` `I` | In most UI fonts `1` has a serif foot or angled flag; `l` is a bare stroke |
| `0` `O` | Zero is narrower; many monospace fonts slash or dot it |
| `rn` `m` | Look for the gap above the join — `m` has none |
| `-` `_` | Check the baseline; underscores sit below it |
| `.` `,` | At the end of a domain this matters; zoom further rather than guess |

When you cannot resolve it, say so and give the alternatives. Two candidate URLs
with a note is useful; one confident wrong URL wastes the person's time.

Shortening services (`bit.ly`, `exitl.ag`, custom vanity domains) are the worst
case, because the path is random characters with no word to sanity-check
against. Treat any shortener read off pixels as provisional unless the
description confirms it.

## Low-contrast or moving overlays

Captions and lower thirds often sit on a translucent panel over moving footage,
so the same text is easy on one frame and unreadable on the next. The fix is
usually a neighbouring frame rather than more zoom: try a second either side.

```
python scripts/zoom.py 4:10 --work work --region bottom --scale 2
python scripts/zoom.py 4:12 --work work --region bottom --scale 2
```

If `--every 2` is too coarse to land on a clean frame, re-run `prepare.py` with
`--every 1` over the stretch that matters.

## Text hidden behind the presenter

Facecam cutouts and animated mascots frequently sit on top of exactly the thing
you want. Nothing recovers pixels that are covered, but the same content is
usually on screen for several seconds, and the overlay moves. Check a few
seconds either side before concluding the text is unrecoverable.

## Scrolling terminals and code

Content that scrolls means no single frame holds all of it. Pull several frames
across the scroll and stitch the content mentally, watching for the overlap so
you do not drop or duplicate a line. If someone wants a long file reproduced
this way, that is usually a sign they should fetch the real source — check
whether the repo URL is on screen and point them at it instead.

## Fast-cutting edits

A two-second sample interval can skip a card that is only on screen for one
second. If a video cuts hard and often, or if the person is sure something was
shown that you did not find, re-run with `--every 1` or `--every 0.5`. It costs
more frames and more time, but missing the one card that mattered costs more.

## Deciding when to stop

Contact sheets are ordered busiest first, so the useful material is usually
front-loaded. Stop when sheets have gone quiet *and* you have found what was
asked for. If you have not found it, the ordering is a ranking and not a
guarantee — keep reading, then widen the sampling rate before concluding the
thing is not there.

## Things that are not worth chasing

- Platform chrome: the YouTube player, view counts, the creator's own subscribe
  button. It is on screen, but it is not information from the video.
- Watermarks and recurring channel branding; note once and move on.
- Stock footage and B-roll captions that belong to the footage, not the content.
