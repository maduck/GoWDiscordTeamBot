import json

from data_source.pet import PetContainer
from data_source.spell import Spell
from data_source.trait import Trait
from data_source.troop import Troop
from data_source.weapon import Weapon
from translations import LANGUAGE_CODE_MAPPING


class Collection:
    def __init__(self, data, user_data=None, world_data=None):
        data_class_name = f'{self.__class__.__name__[:-1]}Container'
        data_class = globals()[data_class_name]

        self.items = {}
        for entry in data:
            item = data_class(entry, user_data, world_data)
            self.items[item.id] = item

    def __contains__(self, key):
        return key in self.items

    def __getitem__(self, item):
        return self.items[item]

    def get(self, key, default=None):
        return default if key not in self.items else self.items[key]

    def search(self, search_term, lang, **kwargs):
        lang = LANGUAGE_CODE_MAPPING.get(lang, lang)
        if search_term.isdigit() and int(search_term) in self.items:
            if item := self.items.get(int(search_term)):
                return [item.translations[lang]]
            return []

        possible_matches = []
        for item in self.items.values():
            if item.matches_precisely(search_term, lang):
                return [item.translations[lang]]
            elif item.matches(search_term, lang, **kwargs):
                possible_matches.append(item.translations[lang])
        return possible_matches

    @classmethod
    def from_json(cls, json_string, user_data=None):
        data = json.loads(json_string)
        return cls(data, user_data=user_data)

    def fill_untranslated_kingdom_name(self, kingdom_id, kingdom_reference_name):
        for item in self.items.values():
            item.fill_untranslated_kingdom_name(kingdom_id, kingdom_reference_name)


class Pets(Collection):
    pass
