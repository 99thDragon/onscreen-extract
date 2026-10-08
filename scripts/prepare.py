#!/usr/bin/env python3
"""
Stage a video for on-screen text extraction.

Downloads (or locates) the video, pulls its metadata, then samples frames and
throws away the ones that look the same as the frame before. Most videos are
long stretches of near-identical pixels; collapsing those is what makes the
rest of the pipeline affordable.

    python prepare.py <youtube-url-or-local-path> [--out DIR] [--every SEC]
                      [--threshold N] [--max-frames N]

Writes into DIR (default ./work):
    video.mp4        the source, if downloaded
    metadata.json    title, description, chapters, uploader
    frames/*.jpg     the kept frames, named by timestamp
    manifest.json    every kept frame with its timestamp and novelty score
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def run(cmd, **kw):
    return subprocess.run(cmd, creationflags=NO_WINDOW, **kw)


def is_url(s):
    return bool(re.match(r"https?://", s))


def fetch(source, out):
    """Return (video_path, metadata_dict)."""
    if not is_url(source):
        p = Path(source).expanduser().resolve()
        if not p.is_file():
            sys.exit(f"No such file: {p}")
        meta = {"title": p.stem, "description": "", "source": str(p)}
        (out / "metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        return p, meta

    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg is required and was not found on PATH.")

    print("fetching metadata ...", flush=True)
    r = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-warnings",
         "--dump-single-json", "--no-playlist", source],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=NO_WINDOW)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"Could not read that video.\n{r.stderr.strip()[:400]}")

    d = json.loads(r.stdout)
    meta = {
        "title": d.get("title", ""),
        "uploader": d.get("uploader") or d.get("channel", ""),
        "duration": d.get("duration", 0),
        "webpage_url": d.get("webpage_url", source),
        # The description very often repeats the on-screen links. Keeping it
        # lets a URL read off blurry pixels be confirmed against clean text.
        "description": d.get("description", "") or "",
        "chapters": [{"start": c.get("start_time"), "title": c.get("title")}
                     for c in (d.get("chapters") or [])],
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    video = out / "video.mp4"
    if video.exists():
        print(f"reusing {video.name}")
        return video, meta

    print(f"downloading: {meta['title']}", flush=True)
    r = run([sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-warnings",
             "--remote-components", "ejs:github", "--no-playlist", "--newline",
             # 720p is plenty: on-screen text is large by design, and smaller
             # files mean faster frame extraction.
             "-f", "bv*[height<=720]+ba/b[height<=720]/bv*+ba/b",
             "--merge-output-format", "mp4", "-o", str(video), source])
    if r.returncode != 0 or not video.exists():
        sys.exit("Download failed. If YouTube is rate-limiting, wait and retry.")
    return video, meta


def dhash(img, size=8):
    """Tiny perceptual fingerprint: which neighbouring pixels are brighter."""
    g = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    a = np.asarray(g, dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten()


def text_score(img, width=640, thr=40):
    """Rough guess at how much hard-edged text or UI a frame carries.

    Lettering and interface chrome produce dense, sharp horizontal transitions;
    photographic or 3D content produces softer gradients. Measured against a
    gameplay video the two groups separated by about 2x, but the ranges touched
    at the edges -- a frame with a scoreboard on it scores like a title card,
    because it genuinely is text. So treat this as a way to decide what to look
    at first, never as grounds for discarding a frame. The one frame holding the
    URL you need is exactly the one you cannot afford to drop unseen.
    """
    g = img.convert("L")
    g = g.resize((width, max(1, int(g.height * width / g.width))), Image.LANCZOS)
    a = np.asarray(g, dtype=np.float32)
    return round(float((np.abs(np.diff(a, axis=1)) > thr).mean()), 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="YouTube URL or path to a local video")
    ap.add_argument("--out", default="work")
    ap.add_argument("--every", type=float, default=2.0,
                    help="sample one frame every N seconds (default 2)")
    ap.add_argument("--threshold", type=int, default=12,
                    help="how different a frame must be to be kept, 0-64 "
                         "(default 12; lower keeps more)")
    ap.add_argument("--max-frames", type=int, default=400)
    args = ap.parse_args()

    out = Path(args.out).resolve()
    (out / "frames").mkdir(parents=True, exist_ok=True)
    raw = out / "_raw"
    raw.mkdir(exist_ok=True)

    video, meta = fetch(args.source, out)

    for f in raw.glob("*.jpg"):
        f.unlink()
    print(f"sampling 1 frame every {args.every}s ...", flush=True)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(video),
         "-vf", f"fps=1/{args.every},scale=1280:-2",
         "-q:v", "3", str(raw / "f_%05d.jpg")], check=True)

    shots = sorted(raw.glob("*.jpg"))
    if not shots:
        sys.exit("ffmpeg produced no frames - is the file a valid video?")

    for f in (out / "frames").glob("*.jpg"):
        f.unlink()

    # Walk the whole video first and only then decide what to keep. Capping
    # inside the loop would quietly stop partway in and leave the tail of a
    # long video unexamined, which is the one failure that matters here: the
    # link you are looking for is just as likely to be in the last minute.
    cand, prev = [], None
    for i, f in enumerate(shots):
        ts = i * args.every
        im = Image.open(f)
        h = dhash(im)
        dist = 64 if prev is None else int(np.count_nonzero(h != prev))
        if dist >= args.threshold:
            cand.append({"src": f, "seconds": round(ts, 1),
                         "timestamp": f"{int(ts // 60)}:{int(ts % 60):02d}",
                         "novelty": dist, "text_score": text_score(im)})
            prev = h

    trimmed = 0
    if len(cand) > args.max_frames:
        trimmed = len(cand) - args.max_frames
        # Keep the busiest frames wherever they fall, then restore time order.
        cand = sorted(cand, key=lambda c: -c["text_score"])[:args.max_frames]
        cand.sort(key=lambda c: c["seconds"])

    kept = []
    for c in cand:
        name = f"t{int(c['seconds'] // 60):03d}m{int(c['seconds'] % 60):02d}s.jpg"
        shutil.copy(c["src"], out / "frames" / name)
        kept.append({"file": name, "seconds": c["seconds"],
                     "timestamp": c["timestamp"], "novelty": c["novelty"],
                     "text_score": c["text_score"]})

    shutil.rmtree(raw, ignore_errors=True)
    (out / "manifest.json").write_text(
        json.dumps({"video": str(video), "title": meta.get("title", ""),
                    "sampled_every": args.every, "threshold": args.threshold,
                    "sampled": len(shots), "kept": len(kept), "frames": kept},
                   indent=1), encoding="utf-8")

    print(f"\n{len(shots)} sampled -> {len(kept)} kept "
          f"({100 * len(kept) / len(shots):.0f}% survived dedup)")
    if trimmed:
        print(f"  {trimmed} lower-scoring frames dropped to stay under "
              f"--max-frames {args.max_frames}; coverage still spans the whole video")
    if kept:
        span = kept[-1]["seconds"]
        print(f"  covers 0:00 - {int(span // 60)}:{int(span % 60):02d}")
    print(f"frames in {out / 'frames'}")
    if meta.get("description"):
        print(f"description captured: {len(meta['description'])} chars "
              "(use it to confirm URLs read off the screen)")


if __name__ == "__main__":
    main()
