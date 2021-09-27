import datetime
import platform
import re
from calendar import day_name, different_locale

from base_bot import log
from translations import LANGUAGE_CODE_MAPPING, LOCALE_MAPPING


def atoi(text):
    return int(text) if text.isdigit() else text


def bool_to_emoticon(value):
    return value and "✅" or "❌"


# https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries
# merges b into a
def merge(a, b, path=None):
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
        else:
            a[key] = b[key]
    return a


def flatten(*args):
    lst = []
    for arg in args:
        if type(arg) == str and arg != '':
            lst.append(arg)
        elif type(arg) == list:
            lst.extend(arg)
    return lst


async def pluralize_author(author):
    if author[-1] == 's':
        author += "'"
    else:
        author += "'s"
    return author


def chunks(iterable, chunk_size):
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i:i + chunk_size]


def dig(item, lookup):
    result = None
    for key in lookup.split('.'):
        result = item.get(key)
        if result is None:
            break
        item = result
    return result


def debug(message):
    guild = '-'
    if message.guild:
        guild = message.guild.name
    log.debug(f'[{guild}][{message.channel}][{message.author.display_name}] {message.content}')


DAMAGE_DENOMINATOR = re.compile(r'\[.+?]', )


def extract_search_tag(search_term):
    if isinstance(search_term, list):
        search_term = ''.join(search_term)
    if search_term is None:
        search_term = ''
    ignored_characters = ' -\'’.,'
    for char in ignored_characters:
        search_term = search_term.replace(char, '')
    search_term = DAMAGE_DENOMINATOR.sub("", search_term)
    return search_term.lower()


def translate_day(day_no, locale):
    locale = LANGUAGE_CODE_MAPPING.get(locale, locale)
    locale = LOCALE_MAPPING.get(locale, 'en_GB') + '.UTF8'
    with different_locale(locale):
        return day_name[day_no]


def get_next_monday_in_locale(date, lang):
    lang = LANGUAGE_CODE_MAPPING.get(lang, lang)
    today = datetime.date.today()
    monday = 0
    if date:
        month, day = date.split('-')
        date = today.replace(month=int(month), day=int(day))
    elif today.weekday() == monday:
        date = today
    else:
        date = today + datetime.timedelta(days=-today.weekday(), weeks=1)
    locale = lang
    if platform.system() != 'Windows':
        locale = LOCALE_MAPPING.get(lang, 'en_GB') + '.UTF8'
    with different_locale(locale):
        formatted_date = date.strftime('%b %d')
    return formatted_date, date


def convert_color_array(data_object):
    return [c.replace('Color', '').lower() for c, v in data_object['ManaColors'].items() if v]


class U(str):
    def __format__(self, fmt):
        if not fmt:
            s = str(self)
        elif fmt[0] == 'u':
            s = self.upper()
            fmt = fmt[1:]
        elif fmt[0] == 'l':
            s = self.lower()
            fmt = fmt[1:]
        else:
            s = str(self)
        return s.__format__(fmt)
