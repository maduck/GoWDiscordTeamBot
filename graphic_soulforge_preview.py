import io
import math
from typing import Mapping

from wand.color import Color
from wand.drawing import Drawing

from graphic_base_preview import BasePreview, FONTS, download_image, scale_down, word_wrap

LESSER_DARK_GRAY = Color('rgb(35, 39, 38)')
DARK_GRAY = Color('rgba(0, 0, 0, 0.7)')


class WeeklyPreview(BasePreview):
    def __init__(self, data):
        super().__init__(data)
        self.weapon = None

    def get_box_coordinates(self, box_number):
        outer_spacing_percentage = 3
        inner_spacing_percentage = 1
        vertical_spacing_percentage = 10
        vertical_spacing = vertical_spacing_percentage * self.img.height / 100
        height = self.img.height - 300 - 2 * vertical_spacing
        top = round(250 + vertical_spacing)

        outer_spacing = outer_spacing_percentage * self.img.width / 100
        inner_spacing = inner_spacing_percentage * self.img.width / 100
        width = round((self.img.width - 2 * outer_spacing - 2 * inner_spacing) / 3)

        left = round(outer_spacing + box_number * (width + inner_spacing))

        return left, top, width, height

    def render_soulforge_screen(self):
        left, top, width, height = self.get_box_coordinates(1)

        self.weapon = download_image(self.data['filename'])
        ratio = self.weapon.width / self.weapon.height
        self.weapon.resize(round(180 * ratio), 180)
        with Drawing() as draw:
            draw.fill_color = Color('none')
            draw.stroke_color = Color('rgb(16, 17, 19)')
            draw.stroke_width = 20
            draw.circle(origin=(self.weapon.width // 2, self.weapon.height // 2),
                        perimeter=(self.weapon.width // 2, -draw.stroke_width // 2))
            draw.border_color = draw.stroke_color
            try:
                draw.matte(0, 0, 'filltoborder')
                draw.matte(self.weapon.width - 1, 0, 'filltoborder')
            except AttributeError:
                draw.alpha(0, 0, 'filltoborder')
                draw.alpha(self.weapon.width - 1, 0, 'filltoborder')
            draw(self.weapon)

        with Drawing() as draw:
            draw.fill_color = DARK_GRAY
            rarity_color = ','.join([str(c) for c in self.data['rarity_color']])
            draw.stroke_color = Color(f'rgb({rarity_color})')
            draw.stroke_width = 8
            draw.rectangle(left, top, left + width, top + height, radius=40)

            draw.fill_color = LESSER_DARK_GRAY
            draw.stroke_color = draw.fill_color
            draw.stroke_width = 0
            draw.circle((left + 300, top + 350), (left + 300, top + 235))
            slot_angles = [48 * x - 258 for x in range(1, 7)]

            requirement_objects = self.extract_requirements()

            hypotenuse = 210
            for i, angle in enumerate(slot_angles):
                draw.fill_color = LESSER_DARK_GRAY
                draw.stroke_color = draw.fill_color
                rad_angle = 2 * math.pi * (90 + angle) / 360
                center = left + 300 - hypotenuse * math.sin(rad_angle), top + 350 - hypotenuse * math.cos(rad_angle)
                perimeter = (center[0], center[1] + 115 // 2)
                draw.stroke_width = 10
                draw.line((left + 300, top + 350), center)
                draw.stroke_width = 0
                draw.circle(center, perimeter)
                if requirement_objects[i]:
                    filename, amount = requirement_objects[i]
                    requirement_img = download_image(filename)
                    max_size = 70
                    r_width, r_height = scale_down(*requirement_img.size, max_size)
                    draw.composite(operator='atop',
                                   left=center[0] - r_width // 2, top=center[1] - r_height // 2,
                                   width=r_width, height=r_height,
                                   image=requirement_img)
                    draw.text_antialias = True
                    draw.stroke_color = Color('rgb(10, 199, 43)')
                    draw.stroke_width = 0
                    draw.fill_color = draw.stroke_color
                    draw.font_size = 35
                    draw.font = FONTS['opensans']
                    draw.text_alignment = 'center'
                    draw.text(round(center[0]), round(center[1] + max_size), f'{amount:,.0f}')

            draw.composite(operator='atop',
                           left=left + 182, top=top + 260,
                           width=self.weapon.width, height=self.weapon.height,
                           image=self.weapon)
            draw.fill_color = Color('none')
            draw.stroke_color = LESSER_DARK_GRAY
            draw.stroke_width = 20
            draw.circle((left + 300, top + 350), (left + 300, top + 250))

            draw.stroke_color = Color('rgb(16, 17, 19)')
            draw.stroke_width = 10
            draw.circle((left + 300, top + 350), (left + 300, top + 255))

            draw.fill_color = Color('white')
            draw.stroke_color = Color('white')
            draw.font = FONTS['opensans']
            draw.font_size = 60
            draw.stroke_width = 0
            draw.text_alignment = 'center'
            draw.text_antialias = True
            name = word_wrap(self.img, draw, self.data['name'], width, int(1.5 * draw.font_size))
            draw.text(left + width // 2, top + 80 - int(60 - draw.font_size), name)

            draw.font_size = 30
            draw.font = FONTS['raleway']
            draw.text_alignment = 'center'
            draw.fill_color = Color('white')
            crafting_message = word_wrap(self.img, draw, self.data["texts"]["in_soulforge"], width - 20, 100)
            text_top = round(top + height - draw.font_size * 2)
            draw.text(left + width // 2, text_top, crafting_message)

            draw(self.img)

    def render_affixes(self):
        affix_icon = download_image(self.data['affix_icon'])
        gold_medal = download_image(self.data['gold_medal'])
        mana = download_image(self.data['mana_color'])
        with Drawing() as draw:
            draw.fill_color = DARK_GRAY
            draw.stroke_width = 0
            left, top, width, height = self.get_box_coordinates(0)
            draw.rectangle(left, top, left + width, top + height, radius=40)

            draw.composite(operator='atop',
                           left=left + 20, top=top + 8,
                           width=mana.width, height=mana.height,
                           image=mana)
            draw.composite(operator='atop', left=left + 10, top=top + 5,
                           width=gold_medal.width, height=gold_medal.height,
                           image=gold_medal)
            draw.font_size = 70
            draw.stroke_width = 0
            draw.text_antialias = True
            draw.text_alignment = 'center'
            draw.font = FONTS['opensans']
            mana_x = left + 20 + mana.width // 2
            mana_y = round(top + 8 + mana.height / 2 + draw.font_size / 3)
            draw.fill_color = Color('black')
            draw.text(mana_x + 2, mana_y + 2, str(self.data['mana_cost']))
            draw.fill_color = Color('white')
            draw.text(mana_x, mana_y, str(self.data['mana_cost']))

            draw.fill_color = Color('white')
            draw.stroke_color = Color('none')
            draw.text_alignment = 'left'
            draw.stroke_width = 0
            base_size = 30
            draw.font_size = base_size
            draw.font = FONTS['raleway']
            description = word_wrap(self.img, draw, self.data['description'], 420, height // 3)
            draw.text(left + 160, top + 25 + 3 * base_size, description)

            draw.text_alignment = 'right'
            draw.font_size = 2 * base_size

            draw.fill_color = Color('white')
            draw.text(left + width - 10, top + 25 + base_size, self.data['type'])

            offset = 375
            x = left + width
            for affix in self.data['affixes']:
                my_affix = affix_icon.clone()
                color_code = ','.join([str(c) for c in affix['color']])
                my_affix.colorize(color=Color(f'rgb({color_code})'), alpha=Color('rgb(100%, 100%, 100%)'))

                draw.fill_color = Color('white')
                draw.composite(operator='atop',
                               left=x - 65, top=top + offset - 3 * base_size // 4,
                               width=affix_icon.width, height=affix_icon.height,
                               image=my_affix)
                draw.font_size = base_size
                draw.font = FONTS['raleway']
                draw.text(x - 70, top + offset, affix['name'])
                draw.font_size = 3 * base_size // 5
                draw.font = FONTS['opensans']
                description = word_wrap(self.img, draw, affix['description'], width - 80, base_size + 10)
                draw.text(x - 70, top + offset + base_size - 5, description)
                offset += 2 * base_size

            draw.font_size = 30
            margin = 100
            box_width = 80
            item_count = len(list(self.data['stat_increases'].values()))
            distance = round((600 - item_count * box_width - 2 * margin) / (item_count - 1))
            icon_top = round(height - 70)
            for i, (stat, increase) in enumerate(self.data['stat_increases'].items()):
                icon_left = left + margin + i * (box_width + distance)
                stat_icon = download_image(self.data['stat_icon'].format(stat=stat))
                width, height = scale_down(*stat_icon.size, max_size=50)
                stat_icon.resize(width=width, height=height)
                draw.text(icon_left + 70, top + icon_top + int(1.1 * draw.font_size), str(increase))
                draw.composite(operator='atop',
                               left=icon_left, top=top + icon_top,
                               width=stat_icon.width, height=stat_icon.height,
                               image=stat_icon
                               )
            draw(self.img)

    def render_farming(self):
        with Drawing() as draw:
            left, top, width, height = self.get_box_coordinates(2)

            draw.fill_color = DARK_GRAY
            draw.stroke_width = 0
            draw.rectangle(left, top, left + width, top + height, radius=40)

            base_size = 35
            draw.font_size = 12 * base_size / 7
            draw.text_antialias = True
            draw.fill_color = Color('white')
            draw.font = FONTS['raleway']
            draw.text(left + 30, top + 25 + base_size, self.data['texts']['resources'])

            draw.font = FONTS['opensans']
            draw.font_size = base_size
            heading = f'{self.data["texts"]["dungeon"]} &\n{self.data["texts"]["kingdom_challenges"]}'
            draw.text(left + 30, top + 25 + 2 * base_size, heading)

            offset = 5 * base_size
            draw.font_size = 30
            draw.font = FONTS['raleway']
            for jewel in self.data['requirements']['jewels']:
                jewel_icon = download_image(jewel['filename'])
                jewel_width, jewel_height = scale_down(jewel_icon.width, jewel_icon.height, 50)
                jewel_icon.resize(width=jewel_width, height=jewel_height)
                draw.composite(operator='atop',
                               left=left + 25, top=top + offset + round(1.5 * draw.font_size),
                               width=jewel_width, height=jewel_height,
                               image=jewel_icon)
                kingdoms = ', '.join(jewel['kingdoms'])

                message_lines = [
                    f'x100 {jewel["available_on"]}: {self.data["texts"]["dungeon_battles"]}',
                    f'x100 {jewel["available_on"]}: {self.data["texts"]["gem_bounty"]} ({self.data["texts"]["n_gems"]})',
                    f'x140 {self.data["texts"]["tier_8"]} {self.data["texts"]["kingdom_challenges"]}:\n{kingdoms}'
                ]
                message = '\n'.join(
                    [word_wrap(self.img, draw, m, width - 2 * jewel_width,
                               7 * (height - 2.5 * base_size) / base_size) for m in
                     message_lines])

                draw.text(left + 25 + 55, top + 30 + offset, message)
                offset += round(2.5 * base_size + draw.font_size * len(message.split('\n')))
            draw(self.img)

    def save_image(self):
        self.img.format = 'png'
        self.img.save(filename='test.png')

    def extract_requirements(self) -> Mapping[str, str]:
        result = [None for _ in range(6)]
        souls = 'Commonrewards_icon_soul_small_full.png'
        result[3] = (souls, self.data['requirements'][souls])
        celestials = 'Runes_Rune39_full.png'
        diamonds = 'Runes_JewelDiamond_full.png'
        jewels = self.data['requirements']['jewels']
        if len(jewels) == 1:
            result[4] = (diamonds, self.data['requirements'][diamonds])
            result[2] = (jewels[0]['filename'], jewels[0]['amount'])
            result[1] = (celestials, self.data['requirements'][celestials])
        elif len(self.data['requirements']['jewels']) == 2:
            result[5] = (celestials, self.data['requirements'][celestials])
            result[2] = (jewels[0]['filename'], jewels[0]['amount'])
            result[4] = (jewels[1]['filename'], jewels[1]['amount'])
            result[1] = (diamonds, self.data['requirements'][diamonds])
        return result


def render_all(result):
    overview = WeeklyPreview(result)
    overview.render_background('{0[texts][soulforge]}: {0[date]}')
    overview.render_soulforge_screen()
    overview.render_affixes()
    overview.render_farming()
    overview.draw_watermark()

    return io.BytesIO(overview.img.make_blob('png'))
