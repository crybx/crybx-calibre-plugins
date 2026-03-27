#!/usr/bin/env python3
"""Generate the MangaUpdates plugin icon.

White Permanent Marker M on #d97f15 orange rounded rectangle.
Rendered at 256px and downscaled to 64px for smooth anti-aliasing.

Requires: pip install Pillow
Font: Permanent Marker (Google Fonts) - place PermanentMarker-Regular.ttf
      in the same directory as this script, or adjust FONT_PATH.
"""

import os
from PIL import Image, ImageDraw, ImageFont

RENDER_SIZE = 256
FINAL_SIZE = 64
BG_COLOR = (217, 127, 21, 255)     # #d97f15
FG_COLOR = (255, 255, 255, 255)    # white
CORNER_RADIUS = 20                  # 20 at 256px = 5px at 64px
FONT_SIZE = 180

SCRIPT_DIR = os.path.dirname(__file__)
FONT_PATH = os.path.join(SCRIPT_DIR, 'PermanentMarker-Regular.ttf')
OUTPUT = os.path.join(SCRIPT_DIR, '..',
                      'calibre_plugins', 'mangaupdates', 'images', 'mangaupdates.png')

img = Image.new('RGBA', (RENDER_SIZE, RENDER_SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle([4, 4, RENDER_SIZE - 5, RENDER_SIZE - 5],
                       radius=CORNER_RADIUS, fill=BG_COLOR)

font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
bbox = draw.textbbox((0, 0), 'M', font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
x = (RENDER_SIZE - tw) / 2 - bbox[0]
y = (RENDER_SIZE - th) / 2 - bbox[1]
draw.text((x, y), 'M', fill=FG_COLOR, font=font)

img = img.resize((FINAL_SIZE, FINAL_SIZE), Image.LANCZOS)
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
img.save(OUTPUT)
print('Saved %s (%d bytes)' % (OUTPUT, os.path.getsize(OUTPUT)))
