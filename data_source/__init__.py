import json

from data_source.pet import PetContainer
from data_source.spell import Spell
from data_source.trait import Trait
from data_source.troop import Troop
from data_source.weapon import Weapon
from translations import LANGUAGE_CODE_MAPPING


class Collection:
    def __init__(self, data):
        data_class_name = self.__class__.__name__[:-1] + 'Container'
        data_class = globals()[data_class_name]

        self.items = {}
        for entry in data:
            item = data_class(entry)
            self.items[item.id] = item

    def __contains__(self, key):
        return key in self.items

    def __getitem__(self, item):
        return self.items[item]

    def get(self, key, default=None):
        if key not in self.items:
            return default
        return self.items[key]

    def search(self, search_term, lang):
        lang = LANGUAGE_CODE_MAPPING.get(lang, lang)
        if search_term.isdigit() and int(search_term) in self.items:
            item = self.items.get(int(search_term))
            if item:
                return [item.translations[lang]]
            return []

        possible_matches = []
        for item in self.items.values():
            if item.matches_precisely(search_term, lang):
                return [item.translations[lang]]
            elif item.matches(search_term, lang):
                possible_matches.append(item.translations[lang])
        return possible_matches

    @classmethod
    def from_json(cls, json_string):
        data = json.loads(json_string)
        return cls(data)

    def fill_untranslated_kingdom_name(self, kingdom_id, kingdom_reference_name):
        for item in self.items.values():
            item.fill_untranslated_kingdom_name(kingdom_id, kingdom_reference_name)


class Pets(Collection):
    pass
