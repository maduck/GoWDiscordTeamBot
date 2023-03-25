import io
import os
from textwrap import wrap

import requests
from wand.color import Color
from wand.drawing import Drawing
from wand.image import Image

BASE_URL = 'https://garyatrics.com/gow_assets'
FONTS = {
    'opensans': r'fonts/OpenSans-Regular.ttf',
    'raleway': r'fonts/Raleway-Regular.ttf',
}


class BasePreview:
    def __init__(self, data):
        self.data = data
        self.img = None
        self.spacing = 0

    def render_background(self, title):
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
            draw.font = FONTS['opensans']
            y_offset = 200
            if '\n' in title:
                y_offset = 120
            draw.text(450, y_offset, title.format(self.data))

            kingdom_logo = download_image(self.data['kingdom_logo'])
            kingdom_width, kingdom_height = scale_down(kingdom_logo.width, kingdom_logo.height, 220)
            kingdom_logo.resize(kingdom_width, kingdom_height)
            draw.composite(operator='atop',
                           left=self.img.width - kingdom_width - 15, top=15,
                           width=kingdom_width, height=kingdom_height,
                           image=kingdom_logo
                           )
            base_font_size = 40
            draw.font_size = base_font_size
            draw.text_alignment = 'center'
            kingdom = word_wrap(self.img, draw, self.data['kingdom'], kingdom_width + 10, int(1.5 * draw.font_size))
            x = self.img.width - kingdom_width // 2 - 15
            y = kingdom_logo.height + int(1.5 * base_font_size)
            draw.text(x, y, kingdom)

            if self.data.get('alternate_kingdom'):
                kingdom_logo = download_image(self.data['alternate_kingdom_logo'])
                kingdom_width, kingdom_height = scale_down(kingdom_logo.width, kingdom_logo.height, 220)
                kingdom_logo.resize(kingdom_width, kingdom_height)
                draw.composite(operator='atop',
                               left=self.img.width - 2 * (kingdom_width + 15) - 15, top=15,
                               width=kingdom_width, height=kingdom_height,
                               image=kingdom_logo
                               )
                draw.font_size = 40
                draw.text_alignment = 'center'
                kingdom = word_wrap(self.img, draw, self.data['alternate_kingdom'], kingdom_width + 10,
                                    int(1.5 * draw.font_size))
                x = int(self.img.width - 2 * (kingdom_width + 15) - 15 + 0.5 * kingdom_width)
                y = kingdom_logo.height + int(1.5 * base_font_size)
                draw.text(x, y, kingdom)

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
            legal_notice = 'Produced by Gary.\nNo redistribution without this notice.'
            draw.fill_color = Color('black')
            draw.text(self.img.width - width - 18, self.img.height - 2 - 2 * int(draw.font_size), legal_notice)
            draw.text(self.img.width - width - 18, self.img.height + 2 - 2 * int(draw.font_size), legal_notice)
            draw.text(self.img.width - width - 18, self.img.height - 2 + 2 * int(draw.font_size), legal_notice)
            draw.text(self.img.width - width - 18, self.img.height + 2 + 2 * int(draw.font_size), legal_notice)
            draw.fill_color = Color('white')
            draw.text(self.img.width - width - 20, self.img.height - 2 * int(draw.font_size), legal_notice)
            draw(self.img)


def download_image(path):
    cache_path = '.cache'
    cache_filename = os.path.join(cache_path, path)
    if os.path.exists(cache_filename):
        f = open(cache_filename, 'rb')
    else:
        url = f'{BASE_URL}/{path}'
        r = requests.get(url)
        r.raise_for_status()
        f = io.BytesIO(r.content)
        cache_subdir = os.path.dirname(cache_filename)
        if not os.path.exists(cache_subdir):
            os.makedirs(cache_subdir)
        with open(cache_filename, 'wb') as cache:
            cache.write(f.read())
        f.seek(0)
    img = Image(file=f)
    img.alpha_channel = True
    f.close()
    return img


def scale_down(width, height, max_size):
    ratio = width / height
    if width > height:
        return max_size, round(max_size / ratio)
    else:
        return round(ratio * max_size), max_size


def word_wrap(image, draw, text, roi_width, roi_height):
    """Break long text to multiple lines, and reduce point size
    until all text fits within a bounding box."""
    mutable_message = text
    iteration_attempts = 100

    def eval_metrics(txt):
        """Quick helper function to calculate width/height of text."""
        metrics = draw.get_font_metrics(image, txt, True)
        return metrics.text_width, metrics.text_height

    while draw.font_size > 0 and iteration_attempts:
        iteration_attempts -= 1
        width, height = eval_metrics(mutable_message)
        if height > roi_height:
            draw.font_size -= 0.75  # Reduce pointsize
            mutable_message = text  # Restore original text
        elif width > roi_width:
            columns = len(mutable_message)
            while columns > 0:
                columns -= 1
                mutable_message = '\n'.join(wrap(mutable_message, columns))
                wrapped_width, _ = eval_metrics(mutable_message)
                if wrapped_width <= roi_width:
                    break
            if columns < 1:
                draw.font_size -= 0.75  # Reduce pointsize
                mutable_message = text  # Restore original text
        else:
            break
    if iteration_attempts < 1:
        raise RuntimeError("Unable to calculate word_wrap for " + text)
    return mutable_message
