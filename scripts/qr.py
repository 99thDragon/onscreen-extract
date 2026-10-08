#!/usr/bin/env python3
"""
Find and decode QR codes in the sampled frames.

Creators often put a link on screen as a QR rather than as text, so a pass that
only reads lettering misses it entirely. A QR is also the one thing here that
genuinely needs a decoder -- everything else can be read by looking.

    python qr.py [--work DIR] [--limit N]

Decoding needs OpenCV, which nothing else here requires:
    python -m pip install opencv-python-headless

Without it this still points at frames that might hold a QR, so the
information is never silently lost.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

try:
    import cv2
    HAVE_CV2 = True
except ImportError:
    HAVE_CV2 = False


def looks_like_qr(path, cell=24):
    """Weak guess at which frames hold a QR, used only when no decoder exists.

    Scores the fraction of tiles that are strongly bimodal -- mostly very dark
    or very light with little in between. On a test video this ranked a
    high-contrast title card above the frames that actually held QR codes, so
    it is only good enough to point a human at a handful of frames. It is
    deliberately not used to decide what the decoder reads; the decoder reads
    every frame, because missing the one frame with the link is the whole
    failure mode worth avoiding.
    """
    g = Image.open(path).convert("L")
    g = g.resize((480, max(1, int(g.height * 480 / g.width))), Image.LANCZOS)
    a = np.asarray(g, dtype=np.float32)
    h, w = a.shape
    a = a[:h // cell * cell, :w // cell * cell]
    if a.size == 0:
        return 0.0
    b = a.reshape(h // cell, cell, w // cell, cell).transpose(0, 2, 1, 3)
    dark = (b < 80).mean(axis=(2, 3))
    light = (b > 175).mean(axis=(2, 3))
    bimodal = (dark + light > 0.92) & (dark > 0.15) & (light > 0.15)
    return round(float(bimodal.mean()), 4)


def decode(path):
    """Decoded strings from one frame, [] if none or no decoder available."""
    if not HAVE_CV2:
        return []
    img = cv2.imread(str(path))
    if img is None:
        return []
    det = cv2.QRCodeDetector()
    for scale in (1, 2, 3):
        im = img if scale == 1 else cv2.resize(
            img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        try:
            ok, texts, _, _ = det.detectAndDecodeMulti(im)
        except cv2.error:
            continue
        if ok:
            found = sorted({t for t in texts if t})
            if found:
                return found
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap frames scanned (0 = all; decoding is cheap)")
    args = ap.parse_args()

    work = Path(args.work).resolve()
    mf = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
    frames = mf["frames"]

    if not HAVE_CV2:
        print("OpenCV is not installed, so nothing can be decoded.")
        print("  python -m pip install opencv-python-headless")
        print()
        scored = sorted(((looks_like_qr(work / "frames" / fr["file"]), fr)
                         for fr in frames), key=lambda s: -s[0])
        print("Frames that might hold a QR - check these by eye. The ranking is")
        print("weak, so treat it as a hint rather than an answer:")
        for s, fr in scored[:8]:
            print(f"  {fr['timestamp']:>7}  qr-likeness {s:.3f}  {fr['file']}")
        return

    todo = frames[:args.limit] if args.limit else frames
    print(f"scanning {len(todo)} frames for QR codes ...", flush=True)

    hits = []
    for fr in todo:
        for text in decode(work / "frames" / fr["file"]):
            hits.append({"timestamp": fr["timestamp"], "seconds": fr["seconds"],
                         "frame": fr["file"], "decoded": text})

    seen, unique = set(), []
    for h in hits:
        if h["decoded"] not in seen:
            seen.add(h["decoded"])
            unique.append(h)

    (work / "qr.json").write_text(json.dumps(unique, indent=1), encoding="utf-8")
    print()
    if unique:
        print(f"decoded {len(unique)} unique QR code(s):")
        for h in unique:
            print(f"  {h['timestamp']:>7}  {h['decoded']}")
    else:
        print(f"no QR codes decoded across {len(todo)} frames.")
        print("If one was visible on a contact sheet, pull it with")
        print("zoom.py --scale 3 and read it directly - a small or partly")
        print("covered QR often defeats the decoder but still scans by phone.")
    print(f"\n-> {work / 'qr.json'}")


if __name__ == "__main__":
    main()
