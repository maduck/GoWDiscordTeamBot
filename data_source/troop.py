from game_constants import TROOP_RARITIES
from util import convert_color_array

traits = {}


class Troop:
    def __init__(self, json_data):
        self.raw_data = json_data
        self.id = json_data['Id']
        self.name = json_data['Name']
        self.colors = []
        self.description = json_data['Description']
        self.spell_id = json_data['SpellId']
        self.traits = [traits.get(trait, {'name': trait, 'description': '-'}) for trait in json_data['Traits']]
        self.colors = sorted(convert_color_array(json_data))
        self.rarity = self.convert_rarity()
        self.types = self.convert_types()
        self.filename = json_data['FileBase']
        self.kingdom = {'Name': ''}
        self.roles = [f'[TROOP_ROLE_{role.upper()}]' for role in json_data['TroopRoleArray']]

    def convert_rarity(self):
        rarity_number = 1
        if self.raw_data['TroopRarity'] in TROOP_RARITIES:
            rarity_number = TROOP_RARITIES.index(self.raw_data['TroopRarity'])
        return f'[RARITY_{rarity_number}]'

    def convert_types(self):
        types = [self.raw_data['TroopType']]
        if 'TroopType2' in self.raw_data:
            types.append(self.raw_data['TroopType2'])
        return [f'[TROOPTYPE_{_type.upper()}]' for _type in types]
