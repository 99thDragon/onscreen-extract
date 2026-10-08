# onscreen-extract

A Claude skill for the information in a video that exists only as pixels — a URL
on screen for four seconds, a repo name in a terminal, a QR code in a sponsor
read. None of that is in the captions, so a transcript pass misses all of it.

Works on a YouTube URL or a local video file.

## Install

**Cloning alone is not enough.** Claude only loads skills from two places, so
the folder has to live in one of them:

| Location | Available in |
|---|---|
| `~/.claude/skills/` | every project |
| `<project>/.claude/skills/` | that project only |

The simplest route is to clone straight into the personal skills directory:

```
mkdir -p ~/.claude/skills
git clone https://github.com/99thDragon/onscreen-extract.git ~/.claude/skills/onscreen-extract
```

It appears in your skill list the **next time you start a session** — skills are
discovered at startup, not mid-conversation.

### If you want the clone somewhere else

Keep the repo wherever you like and link it instead, so you can edit it as a
normal project and still have Claude see it:

```
# macOS / Linux
ln -s /path/to/onscreen-extract ~/.claude/skills/onscreen-extract
```

```
:: Windows - a junction, which does not need admin rights
mklink /J "%USERPROFILE%\.claude\skills\onscreen-extract" "C:\path\to\onscreen-extract"
```

## Requirements

- **Python 3.9+** with `numpy`, `Pillow`, `yt-dlp`
- **ffmpeg** on your PATH
- *Optional:* `opencv-python-headless`, only for decoding QR codes

```
python -m pip install numpy Pillow yt-dlp opencv-python-headless
```

ffmpeg: `winget install Gyan.FFmpeg` · `brew install ffmpeg` ·
`sudo apt install ffmpeg`

Without OpenCV everything else still works; the QR step reports which frames
might hold a code instead of decoding them.

## Using it

Ask Claude for what a video showed and the skill should trigger on its own —
"get the links out of this video", "what site was he demoing", "grab the
commands from this tutorial".

Run by hand if you prefer:

```
python scripts/prepare.py "https://youtube.com/watch?v=..." --out runs/myvideo
python scripts/contact.py --work runs/myvideo
python scripts/qr.py --work runs/myvideo
python scripts/zoom.py 7:42 --work runs/myvideo --region bottom --scale 2
```

## How it works

A 20-minute video is tens of thousands of frames, and reading them one at a
time is hopeless. So: sample, drop near-duplicates, score what is left for how
much hard-edged text it carries, and tile it into contact sheets with the
busiest frames first. Scanning thumbnails is enough to tell *that* a frame has
text on it. Only the interesting moments get pulled back at full resolution to
actually read.

| Script | Job |
|---|---|
| `prepare.py` | download or locate, sample, deduplicate, score |
| `contact.py` | tile into sheets of 25, busiest first |
| `zoom.py` | re-extract one moment, cropped and enlarged |
| `qr.py` | decode QR codes, which cannot be read by eye |

`SKILL.md` has the full workflow and `references/reading-frames.md` covers the
harder cases — low-contrast overlays, text behind a webcam cutout, scrolling
terminals, and characters that look alike in compressed video.

## Two things learned the hard way

Both are the kind of bug that fails silently, and both are written into
`SKILL.md` as warnings:

**Deduplication barely fires on some footage.** Gameplay and handheld video
differ slightly every frame, so almost everything survives perceptual hashing.
Ranking by text-likelihood is what actually narrows it down — and that score is
a ranking signal only, never a filter. On a test video the busiest gameplay
frame tied the quietest text frame, so filtering on it would drop real text.

**Capping the frame count must not truncate.** An early version stopped
sampling once it hit the cap, so a first run covered only 70% of a 22-minute
video and would have missed a QR code at 16:56 entirely. The cap now drops
lowest-scoring frames from across the whole duration, and the script prints the
range it covered so you can confirm.

For the same reason `qr.py` decodes every frame rather than a shortlist. The
pre-filter that would speed it up ranked a high-contrast title card above the
frames that actually held QR codes.

## Example output

`claude-code-video-report.md` is a real run against a 22-minute video — the
format it produces, with every finding timestamped so it can be checked.

## Notes

- Everything runs locally. The only network calls are fetching the video and
  its metadata.
- `runs/` is gitignored: downloaded video, frames and contact sheets are all
  regenerable and can get large.
- Reading pixels is imperfect. Timestamps on every finding exist so a human can
  verify anything that matters.
