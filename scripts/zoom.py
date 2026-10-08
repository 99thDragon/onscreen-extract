#!/usr/bin/env python3
"""
Pull one moment back at full resolution, optionally cropped and enlarged.

Contact sheets are for spotting; this is for reading. A URL that is four
pixels tall in a thumbnail is perfectly legible once you re-extract that
second from the source at native resolution and crop to the corner it sits in.

    python zoom.py 7:42                       whole frame, full res
    python zoom.py 7:42 --region bottom       just the lower third
    python zoom.py 462 --crop 0.5,0.8,1.0,1.0 right half of the bottom strip
    python zoom.py 7:42 --scale 2             enlarge 2x for small text

--crop takes fractions of the frame: left,top,right,bottom, each 0-1.
Named regions cover the usual places text hides.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

REGIONS = {
    "full":    (0.0, 0.0, 1.0, 1.0),
    "top":     (0.0, 0.0, 1.0, 0.25),     # title cards, browser address bars
    "bottom":  (0.0, 0.72, 1.0, 1.0),     # lower thirds, captions, watermarks
    "left":    (0.0, 0.0, 0.40, 1.0),
    "right":   (0.60, 0.0, 1.0, 1.0),     # overlays, sidebars
    "centre":  (0.22, 0.25, 0.78, 0.75),
    "center":  (0.22, 0.25, 0.78, 0.75),
}


def seconds(t):
    if ":" in t:
        parts = [float(p) for p in t.split(":")]
        out = 0.0
        for p in parts:
            out = out * 60 + p
        return out
    return float(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("time", help="timestamp, e.g. 7:42 or 462")
    ap.add_argument("--work", default="work")
    ap.add_argument("--video", help="override the source video path")
    ap.add_argument("--region", choices=sorted(REGIONS), default="full")
    ap.add_argument("--crop", help="left,top,right,bottom as 0-1 fractions")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="enlarge by this factor (try 2 for small text)")
    ap.add_argument("--out", help="output path")
    args = ap.parse_args()

    work = Path(args.work).resolve()
    video = Path(args.video) if args.video else None
    if video is None:
        import json
        mf = work / "manifest.json"
        if not mf.is_file():
            sys.exit("No manifest.json - run prepare.py first, or pass --video.")
        video = Path(json.loads(mf.read_text(encoding="utf-8"))["video"])
    if not video.is_file():
        sys.exit(f"Video not found: {video}")

    if args.crop:
        try:
            l, t, r, b = (float(x) for x in args.crop.split(","))
        except ValueError:
            sys.exit("--crop wants four numbers: left,top,right,bottom")
    else:
        l, t, r, b = REGIONS[args.region]
    if not (0 <= l < r <= 1 and 0 <= t < b <= 1):
        sys.exit("--crop values must satisfy 0 <= left < right <= 1 (same for top/bottom)")

    secs = seconds(args.time)
    tag = args.time.replace(":", "m") + ("" if args.region == "full" and not args.crop
                                         else f"_{args.region if not args.crop else 'crop'}")
    out = Path(args.out) if args.out else work / "zoom" / f"{tag}.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    vf = (f"crop=iw*{r - l}:ih*{b - t}:iw*{l}:ih*{t}"
          if (l, t, r, b) != (0.0, 0.0, 1.0, 1.0) else "null")
    if args.scale != 1.0:
        vf += f",scale=iw*{args.scale}:ih*{args.scale}:flags=lanczos"

    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(secs), "-i", str(video),
           "-vf", vf, "-frames:v", "1", str(out)]
    if subprocess.run(cmd, creationflags=NO_WINDOW).returncode != 0 or not out.is_file():
        sys.exit("ffmpeg could not extract that frame - is the timestamp inside the video?")

    kb = out.stat().st_size // 1024
    print(f"{out}  ({kb} KB)")
    if kb > 1400:
        print("  large image - if it reads poorly, crop tighter instead of scaling up")


if __name__ == "__main__":
    main()
