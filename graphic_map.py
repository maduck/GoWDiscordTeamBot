import io

import requests.exceptions
from wand.color import Color
from wand.drawing import Drawing

from graphic_base_preview import BasePreview, FONTS, download_image


def clamp01(value):
    if value < 0:
        return 0
    if value > 1:
        return 1
    return value


def lerp(a, b, t):
    return a + (b - a) * clamp01(t)


class WorldMap(BasePreview):
    SIZE = 2048

    def __init__(self, data):
        super().__init__(data)
        self.img = None

    def render_map(self):
        self.img = download_image(self.data['water'])
        self.img.alpha_channel = True
        self.img.resize(self.SIZE, self.SIZE)
        world_map = download_image(self.data['map'])
        world_map.resize(self.SIZE, self.SIZE)

        height = download_image(self.data['height'])
        height.alpha_channel = True
        height.resize(self.SIZE, self.SIZE)

        with Drawing() as draw:
            draw.composite(operator='overlay',
                           left=0, top=0,
                           width=self.SIZE, height=self.SIZE,
                           image=height)
            draw.composite(operator=self.data['blend_mode'],
                           left=0, top=0,
                           width=self.SIZE, height=self.SIZE, image=world_map)
            draw(self.img)

    def render_overlays(self):
        with Drawing() as draw:
            color = Color('rgba(0, 0, 0, 0.7)')
            draw.fill_color = color
            draw.rectangle(0, 0, self.SIZE, 200)
            draw.rectangle(0, self.SIZE - 100, self.SIZE, self.SIZE)
            draw.fill_color = Color('white')
            draw.font_size = 100
            draw.text_antialias = True
            draw.font = FONTS['raleway']
            draw.text_alignment = 'center'
            draw.text(self.SIZE // 2, 150, self.data['title'])
            draw(self.img)

    def render_kingdoms(self):
        with Drawing() as draw:
            text_color = Color('white')
            box_color = Color('rgba(0, 0, 0, 0.7)')
            draw.font_size = 30
            draw.text_antialias = True
            draw.font = FONTS['opensans']
            draw.text_alignment = 'center'
            for kingdom in self.data['kingdoms']:
                x, y = kingdom['coordinates']
                t, t2 = x / 2048, y / 2048
                x = 3 / 4 * lerp(x, x, t) + 250
                y = 3 / 4 * lerp(y, y, t2) + 250
                try:
                    icon = download_image(f'Troopcardshields_{kingdom["filename"]}_full.png')
                except requests.exceptions.HTTPError:
                    continue
                draw.composite(operator='atop',
                               left=x - 0.5 * icon.width, top=y - 0.5 * icon.height,
                               width=icon.width, height=icon.height,
                               image=icon)
                metrics = draw.get_font_metrics(self.img, kingdom['name'], False)

                text_x = x
                text_y = y + 0.5 * (icon.width + draw.font_size)
                draw.fill_color = box_color
                draw.rectangle(int(text_x - metrics.text_width / 2 - 15),
                               int(text_y - metrics.text_height + 10),
                               int(text_x + metrics.text_width / 2 + 15),
                               int(text_y + 10),
                               radius=10
                               )
                draw.fill_color = text_color
                draw.text(int(text_x), int(text_y), kingdom['name'])
            draw(self.img)


def render_all(result):
    world_map = WorldMap(result)
    world_map.render_map()
    world_map.render_overlays()
    world_map.render_kingdoms()
    world_map.draw_watermark()

    return io.BytesIO(world_map.img.make_blob('png'))
