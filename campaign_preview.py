import io

from wand.color import Color
from wand.drawing import Drawing
from wand.image import Image

from game_constants import CAMPAIGN_COLORS, TASK_SKIP_COSTS
from search import _
from soulforge_preview import FONTS, download_image, scale_down, word_wrap


class CampaignPreview:
    def __init__(self, data):
        self.data = data
        self.img = None
        self.spacing = 0

    def render_background(self):
        self.img = download_image(self.data['background'])
        self.spacing = self.img.width // 2 - 980
        gow_logo = download_image(self.data['gow_logo'])
        ratio = gow_logo.width / gow_logo.height
        gow_logo.resize(round(200 * ratio), 200)
        switch_logo = Image(filename='switch_logo.png')
        ratio = switch_logo.width / switch_logo.height
        switch_logo.resize(round(100 * ratio), 100)
        with Drawing() as draw:
            color = Color('rgba(0, 0, 0, 0.7)')
            draw.fill_color = color
            draw.rectangle(0, 0, self.img.width, 300)
            draw.composite(operator='atop',
                           left=(300 - gow_logo.height) // 2, top=(300 - gow_logo.height) // 2,
                           width=gow_logo.width, height=gow_logo.height,
                           image=gow_logo)
            if self.data['switch']:
                draw.composite(operator='atop',
                               left=(300 - switch_logo.height) // 2 - 15, top=300 - switch_logo.height - 15,
                               width=switch_logo.width, height=switch_logo.height,
                               image=switch_logo)
            draw.fill_color = Color('white')
            draw.font_size = 100
            draw.text_antialias = True
            draw.font = FONTS['raleway']
            draw.text(450, 200, f'{self.data["texts"]["campaign"]}: {self.data["date"]}')

            kingdom_logo = download_image(self.data['kingdom_logo'])
            kingdom_width, kingdom_height = scale_down(kingdom_logo.width, kingdom_logo.height, 220)
            kingdom_logo.resize(kingdom_width, kingdom_height)
            draw.composite(operator='atop',
                           left=self.img.width - kingdom_width - 15, top=15,
                           width=kingdom_width, height=kingdom_height,
                           image=kingdom_logo
                           )
            draw.font_size = 40
            draw.text_alignment = 'center'
            kingdom = word_wrap(self.img, draw, self.data['kingdom'], kingdom_width + 10, int(1.5 * draw.font_size))
            x = self.img.width - kingdom_width // 2 - 15
            y = kingdom_logo.height + int(1.5 * draw.font_size)
            draw.text(x, y, kingdom)

            draw(self.img)

    def render_tasks(self):
        y = 350
        padding = 230
        x = padding
        if self.data['team']:
            x = 50
        box_width = self.img.width - 2 * padding
        base_font_size = 30
        with Drawing() as draw:
            for category, tasks in self.data['campaigns'].items():
                color = CAMPAIGN_COLORS[category]
                skip_costs = f'{_("[SKIP_TASK]", self.data["lang"])}: {TASK_SKIP_COSTS[category]} {_("[GEMS]", self.data["lang"])}'
                title = f'{_(category, self.data["lang"])} ({skip_costs})'

                box_height = 2 * base_font_size + (base_font_size + 5) * len(tasks) + 20
                draw.fill_color = Color('black')
                draw.rectangle(x + 50, y + 2 * base_font_size + 10, x + 55, y + box_height)

                draw.fill_color = Color(f'rgba({color.r}, {color.g}, {color.b}, 0.8)')
                draw.rectangle(x, y,
                               x + box_width, y + box_height,
                               radius=base_font_size // 2
                               )

                draw.font_size = base_font_size
                draw.font = FONTS['opensans']
                draw.fill_color = Color('black')
                for i, task in enumerate(tasks, start=1):
                    font_y = y + 2 * base_font_size + (base_font_size + 5) * i
                    draw.text_alignment = 'center'
                    draw.text(x + 30, font_y, str(i))
                    draw.text_alignment = 'left'
                    draw.text(x + 70, font_y, task["name"])

                draw.fill_color = Color('white')
                draw.font_size = 2 * base_font_size
                draw.text_antialias = True
                draw.font = FONTS['raleway']
                draw.text(x + 10, y + int(draw.font_size), title)
                y += box_height
            draw(self.img)

    def render_team(self):
        if not self.data['team']:
            return
        width = 360
        x = self.img.width - width - 25
        y = 500
        with Drawing() as draw:
            draw.fill_color = Color(f'rgba(0, 0, 0, 0.8)')
            draw.rectangle(x, y, x + width, y + 400, radius=15)
            draw.fill_color = Color('white')
            draw.font_size = 50
            draw.text_antialias = True
            draw.font = FONTS['raleway']
            draw.text_alignment = 'center'
            draw.text(x + width // 2, y + int(draw.font_size) + 5, self.data['texts']['team'])

            draw.font = FONTS['opensans']
            draw.text_alignment = 'left'
            draw.font_size = 25
            for i, item in enumerate(self.data['team']['troops']):
                mana_url = f'emojis/{item[0]}.png'
                mana = download_image(mana_url)
                mana_width, mana_height = scale_down(mana.width, mana.height, 30)
                mana.resize(mana_width, mana_height)

                draw.composite(operator='atop',
                               left=x + 20, top=y + 80 + i * (mana.height + 15),
                               width=mana.width, height=mana.height,
                               image=mana)
                troop_title = item[1]
                if item[2]:
                    pass

                draw.text(x + 55, int(y + 80 + (i + 0.5) * (mana.height + 15)), troop_title)
            banner_filename = f'Banners/Banners_{self.data["team"]["banner"]["filename"]}_full.png'
            banner = download_image(banner_filename)
            banner_width, banner_height = scale_down(banner.width, banner.height, 120)
            banner.resize(banner_width, banner_height)
            banner_y = y + 80 + 4 * (mana.height + 15)
            draw.composite(operator='atop',
                           left=x + 20, top=banner_y,
                           width=banner.width, height=banner.height,
                           image=banner)
            draw.text(x + 120, banner_y + banner_height // 2, self.data['team']['banner']['name'])
            draw.text(x + 120, banner_y + banner_height // 2 + int(draw.font_size) + 5,
                      f'{self.data["team"]["class_title"]}: {self.data["team"]["class"]}')

            draw(self.img)

    def draw_watermark(self):
        with Drawing() as draw:
            avatar = Image(filename='hawx_transparent.png')
            max_size = 100
            width, height = scale_down(*avatar.size, max_size)
            draw.composite(operator='atop',
                           left=self.img.width - width - 10, top=self.img.height - height - 10,
                           width=width, height=height,
                           image=avatar)

            draw.font_size = 30
            draw.font = FONTS['raleway']
            draw.text_alignment = 'right'
            draw.text_antialias = True
            legal_notice = 'Produced by Hawx & Gary.\nNo redistribution without this notice.'
            draw.fill_color = Color('black')
            draw.text(self.img.width - width - 18, self.img.height - 2 - 2 * int(draw.font_size), legal_notice)
            draw.text(self.img.width - width - 18, self.img.height + 2 - 2 * int(draw.font_size), legal_notice)
            draw.text(self.img.width - width - 18, self.img.height - 2 + 2 * int(draw.font_size), legal_notice)
            draw.text(self.img.width - width - 18, self.img.height + 2 + 2 * int(draw.font_size), legal_notice)
            draw.fill_color = Color('white')
            draw.text(self.img.width - width - 20, self.img.height - 2 * int(draw.font_size), legal_notice)
            draw(self.img)

    def save_image(self):
        self.img.format = 'png'
        self.img.save(filename='test.png')


def render_all(result):
    overview = CampaignPreview(result)
    overview.render_background()
    overview.draw_watermark()
    overview.render_tasks()
    overview.render_team()

    return io.BytesIO(overview.img.make_blob('png'))
