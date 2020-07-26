import json


class Translations:
    BASE_LANG = 'en'
    LANGUAGES = {
        'en': 'English',
        'fr': 'French',
        'de': 'German',
        'ru': 'Russian',
        'it': 'Italian',
        'es': 'Spanish',
        'cn': 'Chinese',
    }

    def __init__(self):
        self.translations = {}
        for lang_code, language in self.LANGUAGES.items():
            filename = f'GemsOfWar_{language}.json'
            with open(filename, encoding='utf8') as f:
                self.translations[lang_code] = json.load(f)

    def get(self, key, lang=''):
        if lang not in self.translations:
            lang = self.BASE_LANG

        return self.translations[lang].get(key, key)


t = Translations()
_ = t.get
