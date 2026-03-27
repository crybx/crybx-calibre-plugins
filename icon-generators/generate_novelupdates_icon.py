#!/usr/bin/env python3
"""Generate the NovelUpdates plugin icon.

White serif bold N on #2c3e50 rounded rectangle.
Rendered at 256px and downscaled to 64px for smooth anti-aliasing.

Requires: pip install Pillow
Font: DejaVu Serif Bold (system font)
"""

import os
from PIL import Image, ImageDraw, ImageFont

RENDER_SIZE = 256
FINAL_SIZE = 64
BG_COLOR = (44, 62, 80, 255)       # #2c3e50
FG_COLOR = (255, 255, 255, 255)    # white
CORNER_RADIUS = 20                  # 20 at 256px = 5px at 64px
FONT_SIZE = 168
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'

OUTPUT = os.path.join(os.path.dirname(__file__), '..',
                      'calibre_plugins', 'novelupdates', 'images', 'novelupdates.png')

img = Image.new('RGBA', (RENDER_SIZE, RENDER_SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle([4, 4, RENDER_SIZE - 5, RENDER_SIZE - 5],
                       radius=CORNER_RADIUS, fill=BG_COLOR)

font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
bbox = draw.textbbox((0, 0), 'N', font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
x = (RENDER_SIZE - tw) / 2 - bbox[0]
y = (RENDER_SIZE - th) / 2 - bbox[1]
draw.text((x, y), 'N', fill=FG_COLOR, font=font)

img = img.resize((FINAL_SIZE, FINAL_SIZE), Image.LANCZOS)
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
img.save(OUTPUT)
print('Saved %s (%d bytes)' % (OUTPUT, os.path.getsize(OUTPUT)))
