import io

from wand.color import Color
from wand.drawing import Drawing

from game_constants import CAMPAIGN_COLORS
from graphic_base_preview import BasePreview, FONTS, download_image, scale_down, word_wrap
from search import _


class CampaignPreview(BasePreview):
    def __init__(self, data):
        super().__init__(data)

    def render_tasks(self):
        y = 350
        padding = 230
        x = 50 if self.data['team'] else padding
        box_width = self.img.width - 2 * padding
        base_font_size = 30
        with Drawing() as draw:
            for category, tasks in self.data['campaigns'].items():
                color = CAMPAIGN_COLORS[category]
                skip_costs = f'{_("[SKIP_TASK]", self.data["lang"])}: {self.data["task_skip_costs"][category]} {_("[GEMS]", self.data["lang"])}'
                title = f'{_(category, self.data["lang"])} ({skip_costs})'

                box_height = 2 * base_font_size + (base_font_size + 5) * len(tasks) + 20
                draw.fill_color = Color('black')
                draw.rectangle(x + 55, y + 2 * base_font_size + 10, x + 60, y + box_height)

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
                    task_number = f'{title[0]}{i}'
                    draw.text(x + 30, font_y, task_number)
                    draw.text_alignment = 'left'
                    task_name = word_wrap(self.img, draw, task['name'], box_width - 60, 50)
                    draw.text(x + 70, font_y, task_name)

                draw.fill_color = Color('white')
                draw.font_size = 2 * base_font_size
                draw.text_antialias = True
                draw.font = FONTS['raleway']
                draw.text(x + 10, int(y + draw.font_size), title)
                y += box_height
            draw(self.img)

    def render_team(self):
        if not self.data['team']:
            return
        width = 360
        x = self.img.width - width - 25
        y = 500
        with Drawing() as draw:
            draw.fill_color = Color('rgba(0, 0, 0, 0.8)')
            draw.rectangle(x, y, x + width, y + 400, radius=15)
            draw.fill_color = Color('white')
            draw.font_size = 50
            draw.text_antialias = True
            draw.font = FONTS['raleway']
            draw.text_alignment = 'center'
            draw.text(x + width // 2, int(y + draw.font_size + 5), self.data['texts']['team'])

            draw.font = FONTS['opensans']
            draw.text_alignment = 'left'
            draw.font_size = 25
            for i, item in enumerate(self.data['team']['troops']):
                mana_url = f'emojis/{item["color_code"]}.png'
                mana = download_image(mana_url)
                mana_width, mana_height = scale_down(mana.width, mana.height, 30)
                mana.resize(mana_width, mana_height)

                draw.composite(operator='atop',
                               left=x + 20, top=y + 80 + i * (mana.height + 15),
                               width=mana.width, height=mana.height,
                               image=mana)

                draw.text(x + 55, int(y + 80 + (i + 0.5) * (mana.height + 15)), item['name'])
            banner_filename = f'Banners/Banners_{self.data["team"]["banner"]["filename"]}_full.png'
            banner = download_image(banner_filename)
            banner_width, banner_height = scale_down(banner.width, banner.height, 120)
            banner.resize(banner_width, banner_height)
            banner_y = y + 80 + 4 * (mana.height + 15)
            draw.composite(operator='atop',
                           left=x + 20, top=banner_y,
                           width=banner.width, height=banner.height,
                           image=banner)
            banner_text = self.data['team']['banner']['name']
            banner_text = word_wrap(self.img, draw, banner_text, width - 90, banner_height)
            draw.text(x + 120, banner_y + 25, banner_text)

            if self.data['team']['class']:
                class_text = self.data['team']['class']
                class_text = word_wrap(self.img, draw, class_text, width - 90, banner_height)
                draw.text(x + 120, int(banner_y + 4 * draw.font_size), class_text)

            draw(self.img)

    def render_campaign_name(self):
        with Drawing() as draw:
            draw.font = FONTS['raleway']
            draw.text_alignment = 'left'
            draw.text_antialias = True
            draw.font_size = 50
            draw.fill_color = Color('black')
            x = 50
            y = self.img.height - 60
            draw.fill_color = Color('white')
            draw.text_under_color = Color('#00000066')
            draw.text(x, y, f'  {self.data["campaign_name"]}  ')
            draw(self.img)

    def save_image(self):
        self.img.format = 'png'
        self.img.save(filename='test.png')


def render_all(result):
    overview = CampaignPreview(result)
    overview.render_background('{0[texts][campaign]} {0[week]}, {0[date]}')
    overview.draw_watermark()
    overview.render_tasks()
    overview.render_team()
    overview.render_campaign_name()

    return io.BytesIO(overview.img.make_blob('png'))
