#!/usr/bin/env python3
"""
Tile the kept frames into a few large contact sheets.

Reading 150 frames one at a time is slow and expensive. Reading six sheets of
25 is fast, and spotting "that one has a URL on it" only needs a thumbnail.
Each tile is stamped with its timestamp so anything interesting can be pulled
back at full resolution with zoom.py.

    python contact.py [--work DIR] [--cols 5] [--rows 5] [--tile 460]
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size):
    for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttc", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--rows", type=int, default=5)
    ap.add_argument("--tile", type=int, default=460, help="tile width in px")
    ap.add_argument("--order", choices=("score", "time"), default="score",
                    help="score puts the most text-heavy frames on sheet 1 "
                         "so you can stop early; time keeps chronological order")
    args = ap.parse_args()

    work = Path(args.work).resolve()
    manifest = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
    frames = manifest["frames"]
    if args.order == "score" and frames and "text_score" in frames[0]:
        frames = sorted(frames, key=lambda f: -f["text_score"])
    if not frames:
        raise SystemExit("No frames in the manifest - run prepare.py first.")

    sheets_dir = work / "sheets"
    sheets_dir.mkdir(exist_ok=True)
    for f in sheets_dir.glob("*.jpg"):
        f.unlink()

    tw = args.tile
    th = int(tw * 9 / 16)
    bar = 26                      # strip under each tile for the timestamp
    per = args.cols * args.rows
    fnt = font(17)

    made = []
    for s in range((len(frames) + per - 1) // per):
        chunk = frames[s * per:(s + 1) * per]
        cols, rows = args.cols, (len(chunk) + args.cols - 1) // args.cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + bar)), (16, 16, 20))
        d = ImageDraw.Draw(sheet)

        for i, fr in enumerate(chunk):
            x, y = (i % cols) * tw, (i // cols) * (th + bar)
            im = Image.open(work / "frames" / fr["file"]).convert("RGB")
            im.thumbnail((tw - 4, th - 4), Image.LANCZOS)
            sheet.paste(im, (x + 2, y + 2))
            d.rectangle([x, y + th, x + tw, y + th + bar], fill=(28, 28, 40))
            label = fr["timestamp"]
            if args.order == "score" and "text_score" in fr:
                label += f"   {fr['text_score']:.3f}"
            d.text((x + 7, y + th + 4), label, font=fnt, fill=(255, 226, 52))

        name = f"sheet_{s + 1:02d}.jpg"
        sheet.save(sheets_dir / name, quality=88)
        made.append((name, len(chunk), sheet.size))

    print(f"{len(frames)} frames -> {len(made)} sheet(s) in {sheets_dir}"
          + (" (busiest first)" if args.order == "score" else " (chronological)"))
    for name, n, size in made:
        print(f"  {name}  {n} frames  {size[0]}x{size[1]}")
    print("\nRead these, note the timestamps worth a closer look, "
          "then pull them with zoom.py")


if __name__ == "__main__":
    main()
