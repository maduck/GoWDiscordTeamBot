import copy

import translations
from util import dig, extract_search_tag

_ = translations.Translations().get


class BaseGameData:
    def __init__(self):
        self.raw_data = {}
        self.translations = {}

    def translate_one(self, lang):
        item = copy.deepcopy(self.raw_data)
        self.deep_translate(item, lang)
        self.translations[lang] = item

    def translate_all(self):
        for lang in translations.LOCALE_MAPPING.keys():
            self.translate_one(lang)

    @staticmethod
    def is_untranslated(param):
        if not param:
            return True
        return param[0] + param[-1] == '[]'

    def __getattr__(self, item):
        return self.raw_data[item]

    @classmethod
    def deep_translate(cls, data: dict, lang):
        for key, item in data.items():
            new_key = _(key, lang)
            data[new_key] = item
            if key != new_key:
                del data[key]
            if isinstance(item, str) and cls.is_untranslated(item):
                data[new_key] = _(item, lang)
            if isinstance(item, dict):
                cls.translate_drop_chances(data[new_key], lang)

    def set_release_date(self, release_date):
        self.raw_data['release_date'] = release_date
        for lang in translations.LOCALE_MAPPING.keys():
            self.translations[lang]['release_date'] = release_date

    def matches(self, search_term, lang):
        compacted_search = extract_search_tag(search_term)
        item = self.translations[lang]
        if item['name'] == '`?`':
            return False
        lookups = {
            k: extract_search_tag(dig(item, k)) for k in self.LOOKUP_KEYS
        }
        for key, lookup in lookups.items():
            if compacted_search in lookup:
                return True
        return False

    def matches_precisely(self, search_term, lang):
        return extract_search_tag(self.translations[lang]['name']) == extract_search_tag(search_term)
