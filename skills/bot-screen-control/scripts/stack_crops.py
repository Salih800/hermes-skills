#!/usr/bin/env python3
"""Ayni bolgeyi N ekran goruntusunden kirpip tek bir kompozit goruntu yapar.

Amac: N kareyi tek vizyon cagrisinda okumak (ayri ayri sormak yerine).

Kullanim:
  python3 stack_crops.py --box 940,160,1440,205 --scale 2 --out /tmp/titles.png a.png b.png c.png

--box   x1,y1,x2,y2 (tum karelerde ayni yer olmali)
--scale buyutme carpani (kucuk yazi icin 2-3 iyi)
--out   cikti yolu (yazdirilir)
--label opsiyonel: dosya adlarini sol kenara yazar
"""
import argparse
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("PIL yok: python3 -m pip install pillow")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--box", required=True, help="x1,y1,x2,y2")
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", action="store_true", help="dosya adini seridin soluna yaz")
    ap.add_argument("images", nargs="+")
    a = ap.parse_args()

    try:
        x1, y1, x2, y2 = [int(v) for v in a.box.split(",")]
    except ValueError:
        sys.exit("--box x1,y1,x2,y2 seklinde olmali")

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

    label_w = 0
    if a.label:
        label_w = 120
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
