#!/usr/bin/env python3
"""Regenerate the bundled Garmin label fonts; normal builds use checked-in assets.

Install garmin/assets/fonts/requirements.txt in a local virtual environment first.
"""
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "garmin/assets/fonts/IBMPlexMono-Medium.woff2"
OUT = ROOT / "garmin/resources/fonts"
CHARS = "".join(chr(c) for c in range(32, 127)) + "".join(chr(c) for c in range(0x400, 0x460)) + "×–—…·"


def build(name, size):
    source = TTFont(SOURCE)
    source.flavor = None
    ttf = BytesIO()
    source.save(ttf)
    ttf.seek(0)
    font = ImageFont.truetype(ttf, size)
    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    cell_w = max(font.getbbox(c)[2] - font.getbbox(c)[0] for c in CHARS) + 4
    cell_h = line_height + 4
    cols = 512 // cell_w
    rows = (len(CHARS) + cols - 1) // cols
    atlas = Image.new("L", (512, rows * cell_h))
    draw = ImageDraw.Draw(atlas)
    records = []
    for i, char in enumerate(CHARS):
        left, top, right, bottom = font.getbbox(char)
        x, y = (i % cols) * cell_w + 2, (i // cols) * cell_h + 2
        draw.text((x - left, y - top), char, font=font, fill=255)
        records.append(f"char id={ord(char)} x={x} y={y} width={right-left} height={bottom-top} xoffset={left} yoffset={top} xadvance={round(font.getlength(char))} page=0 chnl=15")
    atlas.save(OUT / f"{name}.png")
    header = [f'info face="OpenGym Mono" size={size} bold=0 italic=0 charset="" unicode=1 stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing=0,0',
              f"common lineHeight={line_height} base={ascent} scaleW={atlas.width} scaleH={atlas.height} pages=1 packed=0",
              f'page id=0 file="{name}.png"', f"chars count={len(records)}"]
    (OUT / f"{name}.fnt").write_text("\n".join(header + records) + "\n")


OUT.mkdir(parents=True, exist_ok=True)
for name, size in [("small-amoled", 22), ("title-amoled", 28), ("small-solar", 14), ("title-solar", 18)]:
    build(name, size)
