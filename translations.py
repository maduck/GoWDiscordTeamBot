from game_assets import GameAssets

LANGUAGES = {
    'en': 'English',
    'fr': 'French',
    'de': 'German',
    'ru': 'Russian',
    'ру': 'Russian',
    'it': 'Italian',
    'es': 'Spanish',
    'zh': 'Chinese',
    'cn': 'Chinese',
}

LANGUAGE_CODE_MAPPING = {
    'ру': 'ru',
    'cn': 'zh',
}

LANG_FILES = [f'GemsOfWar_{language}.json' for language in LANGUAGES.values()]


class Translations:
    BASE_LANG = 'en'

    def __init__(self):
        self._translations = {}
        for lang_code, language in LANGUAGES.items():
            self._translations[lang_code] = GameAssets.load(
                f'GemsOfWar_{language}.json')

    def get(self, key, lang=''):
        if lang not in self._translations:
            lang = self.BASE_LANG

        return self._translations[lang].get(key, key)
