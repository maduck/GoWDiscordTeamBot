import io

import requests
from PIL import Image, ImageDraw

BASE_URL = 'https://garyatrics.com/gow_assets'

kingdom_id = 'K27'
header = 'Weekly Event'  # "[WEEKLY_EVENT]"

background_url = f'{BASE_URL}/Background/{kingdom_id}_full.png'
r = requests.get(background_url)
f = io.BytesIO(r.content)
img = Image.open(f).convert('RGBA')
overlay = Image.new('RGBA', img.size, (0, 0, 0, 128))
draw = ImageDraw.Draw(overlay)

overlay_color = (0, 0, 0, 170)
draw.rectangle(
    (0, 0, img.size[0], 300),
    fill=overlay_color,
    outline=None)
img = Image.alpha_composite(img, overlay)
img.show()

img.save('test.png')
