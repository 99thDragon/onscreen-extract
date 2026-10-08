---
name: onscreen-extract
description: Pull links, URLs, QR codes and on-screen text out of a video — the stuff shown on screen rather than spoken. Use this whenever someone wants what was displayed in a video: a URL or repo someone "put on screen", a tool or site shown in a demo, text from slides, terminal output, dashboards, settings menus or browser address bars, or a QR code they could not scan in time. Also use it for "what links were in that video", "what site was he showing", "grab the commands from this tutorial", "what was that tool called", or when someone pastes a YouTube link and wants the information out of it rather than a summary of the talking. Works on a YouTube URL or a local video file. Reach for this even when the request does not mention frames, OCR or screenshots — most people just say "get the links out of this video".
---

# Extracting what a video shows

Spoken words are easy to get at; what is *shown* is not. The URL a creator put on
screen for four seconds, the repo name in a terminal, the QR code in a sponsor
read — none of that is in the captions, and a transcript pass will miss all of
it. This skill gets at the pixels.

The whole problem is volume. A 20-minute video is tens of thousands of frames,
and reading them one at a time is hopeless. What works is looking at many frames
at once in thumbnail form, which is enough to tell *that* a frame has text on it,
then pulling back only the interesting moments at full resolution to read them.

## Workflow

Run these from the skill's `scripts/` directory. Each writes into a work
directory you choose, so several videos can be in flight at once.

### 1. Stage the video

```
python scripts/prepare.py <youtube-url-or-local-path> --out work
```

Downloads at 720p (on-screen text is large by design, and smaller files sample
far faster), grabs the metadata, samples a frame every 2 seconds, drops frames
that look identical to the one before, and scores what is left for how much
hard-edged text it seems to carry.

Useful flags: `--every 1` for a dense, fast-cutting video; `--threshold` to tune
deduplication (lower keeps more); `--max-frames` to cap the total.

Two things worth knowing about the output:

- **Deduplication may barely fire.** On gameplay, handheld or heavily animated
  footage every frame differs slightly, so almost everything survives. That is
  not a failure — the text ranking is what narrows things down.
- **The cap never truncates.** If there are more frames than `--max-frames`, the
  lowest-scoring ones are dropped from across the whole video rather than the
  tail being cut off. Coverage always spans the full duration, and the script
  prints the range so you can confirm it.

### 2. Read the contact sheets

```
python scripts/contact.py --work work
```

Tiles the frames into sheets of 25, busiest first, each tile stamped with its
timestamp. Read sheet_01.jpg, then sheet_02.jpg, and so on.

Because they are ordered by text score, sponsor cards, terminals and slides tend
to land on the first sheet or two and plain footage on the last ones. You can
usually stop once the sheets go quiet — but if what you are looking for has not
turned up, keep going rather than assuming it is not there.

What you are doing here is only spotting. Thumbnail text is rarely legible and
you should not try to read a URL off one; note the timestamp and move on.

### 3. Pull the interesting moments back

```
python scripts/zoom.py 7:42 --work work
python scripts/zoom.py 7:42 --work work --region bottom
python scripts/zoom.py 7:42 --work work --region top
python scripts/zoom.py 7:42 --work work --crop 0.5,0.0,1.0,0.4 --scale 2
```

Re-extracts that second from the source at native resolution, so a URL that was
four pixels tall in a thumbnail becomes readable.

**Crop before you scale.** Enlarging a whole frame makes a huge image that gets
downsampled again when you look at it, which gains nothing. Cropping to the
corner the text sits in and then scaling 2x is what actually makes small text
legible. Named regions (top, bottom, left, right, centre) cover the usual hiding
places; `--crop` takes fractions for anything else.

### 4. Decode any QR codes

```
python scripts/qr.py --work work
```

Creators often put a link on screen as a QR instead of as text, and that is the
one thing here you cannot read by looking. This scans every frame, so it takes
around half a minute on a long video; that is the right trade, because the
pre-filter that would speed it up is not reliable enough to trust.

Needs opencv-python-headless. Without it the script still reports which frames
might hold a QR so nothing is silently lost — but install it if you can, since
the fallback ranking is weak.

### 5. Cross-check against the description

`metadata.json` holds the video's description, which very often repeats the links
shown on screen. This matters more than it sounds: a URL read off blurry pixels
is a guess, and `rn` against `m`, or `l` against `1`, are easy to get wrong. If
the same link appears in the description you have clean text to confirm against.
Say which links were confirmed that way and which were not.

The description also frequently holds links that never appear on screen at all.
Those are worth reporting separately — they often answer the underlying question
even though they are not strictly "on screen".

## Reporting what you found

Lead with the links, since that is usually the point:

```markdown
## Links

| URL | Where | Confirmed |
|---|---|---|
| https://example.com | on screen 4:12 | yes — also in description |
| https://other.dev | QR code 16:56 | decoded, not in description |

## Also in the description, never shown on screen
- ...

## What was on screen
- **3:40** — what is being shown and why it matters
```

Some things worth holding to:

- **Give every finding a timestamp.** It lets the person jump straight there and
  check you, which matters because some of this is read off imperfect pixels.
- **Say when you are unsure.** "Possibly exitl.ag/ao25nxrth, partly obscured at
  2:48" is far more useful than a confident wrong URL. Flag the characters you
  doubt rather than silently picking one.
- **Do not transcribe wholesale.** If a frame shows a page of someone's
  documentation, summarise what it covers and note the timestamp. Copying out
  screen after screen of another person's writing is not what was asked for.
- **Report what is shown, not what is said.** The audio is a separate job; if
  someone wants the spoken content too, transcribe it separately and say so.

## When this is the wrong tool

If the person wants a summary of what the video is *about*, the spoken transcript
is the right source and this is a slow detour. This skill earns its keep when the
information exists only as pixels.

## Reference

`references/reading-frames.md` covers the harder cases: low-contrast overlays,
text behind a webcam cutout, fast-cutting edits, scrolling terminals, and telling
apart characters that look alike in compressed video.
