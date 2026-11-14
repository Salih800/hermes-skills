#!/usr/bin/env python3
"""Stack the same region of N screenshots into one composite image.

Goal: read N frames in a single vision call instead of one call per frame.

Usage:
  python3 stack_crops.py --box 940,160,1440,205 --scale 2 --out /tmp/titles.png a.png b.png c.png

--box   x1,y1,x2,y2 (must land on the same place in every frame)
--scale upscale factor (2-3 works well for small text)
--out   output path (printed when done)
--label optional: write each file name in the left margin
"""
import argparse
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("PIL missing: python3 -m pip install pillow")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--box", required=True, help="x1,y1,x2,y2")
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", action="store_true", help="write the file name in the left margin")
    ap.add_argument("images", nargs="+")
    a = ap.parse_args()

    try:
        x1, y1, x2, y2 = [int(v) for v in a.box.split(",")]
    except ValueError:
        sys.exit("--box must look like x1,y1,x2,y2")

    strips = []
    for path in a.images:
        im = Image.open(path).convert("RGB")
        w, h = im.size
        bx1, by1 = max(0, min(x1, w)), max(0, min(y1, h))
        bx2, by2 = max(bx1 + 1, min(x2, w)), max(by1 + 1, min(y2, h))
        crop = im.crop((bx1, by1, bx2, by2))
        if a.scale != 1:
            crop = crop.resize((int(crop.width * a.scale), int(crop.height * a.scale)))
        strips.append((path, crop))

    label_w = 120 if a.label else 0
    W = max(c.width for _, c in strips) + label_w
    sep = 3
    H = sum(c.height for _, c in strips) + sep * (len(strips) - 1)
    out = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(out)
    y = 0
    for i, (path, c) in enumerate(strips):
        if a.label:
            draw.text((4, y + max(0, c.height // 2 - 6)), path.rsplit("/", 1)[-1], fill="black")
        out.paste(c, (label_w, y))
        y += c.height
        if i != len(strips) - 1:
            draw.rectangle([0, y, W, y + sep - 1], fill="#444444")
            y += sep
    out.save(a.out)
    print(a.out, out.size)


if __name__ == "__main__":
    main()
