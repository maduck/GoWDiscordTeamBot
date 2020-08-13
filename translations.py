import json

LANGUAGES = {
    'en': 'English',
    'fr': 'French',
    'de': 'German',
    'ru': 'Russian',
    'it': 'Italian',
    'es': 'Spanish',
    'cn': 'Chinese',
}

LANG_FILES = [f'GemsOfWar_{language}.json' for language in LANGUAGES.values()]


class Translations:
    BASE_LANG = 'en'

    def __init__(self):
        self._translations = {}
        for lang_code, language in LANGUAGES.items():
            filename = f'GemsOfWar_{language}.json'
            with open(filename, encoding='utf8') as f:
                self._translations[lang_code] = json.load(f)

    def get(self, key, lang=''):
        if lang not in self._translations:
            lang = self.BASE_LANG

        return self._translations[lang].get(key, key)
