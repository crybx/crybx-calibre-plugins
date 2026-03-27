#!/usr/bin/env python3
"""Generate the MangaDex plugin icon.

MangaDex fox/eye logo from their official SVG on a #272b30 dark circle.
Rendered at 256px and downscaled to 64px for smooth anti-aliasing.

Requires: pip install Pillow cairosvg
Logo source: https://mangadex.org/img/brand/mangadex-logo.svg
             Place mangadex-logo.svg in the same directory as this script.
"""

import os
import io
import cairosvg
from PIL import Image, ImageDraw

RENDER_SIZE = 256
FINAL_SIZE = 64
BG_COLOR = (39, 43, 48, 255)   # #272b30
LOGO_PADDING = 40               # padding inside the circle

SCRIPT_DIR = os.path.dirname(__file__)
SVG_PATH = os.path.join(SCRIPT_DIR, 'mangadex-logo.svg')
OUTPUT = os.path.join(SCRIPT_DIR, '..',
                      'calibre_plugins', 'mangadex', 'images', 'mangadex.png')

# Render SVG at high res
png_data = cairosvg.svg2png(url=SVG_PATH, output_width=512, output_height=436)
logo = Image.open(io.BytesIO(png_data)).convert('RGBA')
bbox = logo.getbbox()
if bbox:
    logo = logo.crop(bbox)

# Create canvas with circle background
canvas = Image.new('RGBA', (RENDER_SIZE, RENDER_SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(canvas)
draw.ellipse([4, 4, RENDER_SIZE - 5, RENDER_SIZE - 5], fill=BG_COLOR)

# Scale logo to fit inside circle
max_w = RENDER_SIZE - LOGO_PADDING * 2
max_h = RENDER_SIZE - LOGO_PADDING * 2
ratio = min(max_w / logo.width, max_h / logo.height)
new_w = int(logo.width * ratio)
new_h = int(logo.height * ratio)
logo = logo.resize((new_w, new_h), Image.LANCZOS)

# Center and paste
x = (RENDER_SIZE - new_w) // 2
y = (RENDER_SIZE - new_h) // 2
canvas.paste(logo, (x, y), logo)

# Downscale
icon = canvas.resize((FINAL_SIZE, FINAL_SIZE), Image.LANCZOS)
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
icon.save(OUTPUT)
print('Saved %s (%d bytes)' % (OUTPUT, os.path.getsize(OUTPUT)))
