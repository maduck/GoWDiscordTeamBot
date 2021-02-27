from data_source.base_game_data import BaseGameData, BaseGameDataContainer
from game_constants import COLORS
from util import convert_color_array

EFFECTS = (
    '[PETTYPE_BUFFTEAMCOLOR]',
    '[PETTYPE_BUFFGEMMASTERY]',
    '[PETTYPE_BUFFTEAMKINGDOM]',
    '[PETTYPE_BUFFTEAMTROOPTYPE]',
    '[PETTYPE_LOOTSOULS]',
    '[PETTYPE_LOOTGOLD]',
    '[PETTYPE_LOOTXP]',
    '[PETTYPE_NOEFFECT]',
)


class Pet(BaseGameData):
    pass


class PetContainer(BaseGameDataContainer):
    DATA_CLASS = Pet
    LOOKUP_KEYS = ['name', 'kingdom']

    def __init__(self, data):
        super().__init__()
        self.data = {
            'id': data['Id'],
            'name': data['Name'],
            'colors': convert_color_array(data),
            'color_code': ''.join(convert_color_array(data)),
            'effect': EFFECTS[data['Effect']],
            'effect_data': data.get('EffectData'),
            'effect_title': '[PET_TYPE]',
            'troop_type': data.get('EffectTroopType'),
            'reference_name': data['ReferenceName'],
            'filename': data['FileBase'],
            'kingdom_id': data['KingdomId'],
            'kingdom': f'[{data["KingdomId"]}_NAME]',
            'kingdom_title': '[KINGDOM]',
        }
        self.populate_effect_data()
        self.translate()

    def populate_effect_data(self):
        effect = self.data['effect']
        if effect == '[PETTYPE_BUFFTEAMKINGDOM]':
            self.data['effect_data'] = f'[{self.data["effect_data"]}_NAME]'
        elif effect == '[PETTYPE_BUFFTEAMTROOPTYPE]':
            troop_type = self.data['troop_type'].upper()
            self.data['effect_data'] = f'[TROOPTYPE_{troop_type}]'
        elif effect == '[PETTYPE_BUFFTEAMCOLOR]':
            color = self.data['colors'][0].upper()
            self.data['effect'] = f'[PET_{color}_BUFF]'
            self.data['effect_data'] = None
        elif effect == '[PETTYPE_BUFFGEMMASTERY]':
            if self.data['effect_data']:
                color = COLORS[self.data['effect_data']].upper()
                self.data['effect'] = f'[PET_{color}_BUFF]'
                self.data['effect_data'] = None
            else:
                self.data['effect'] = f'[PET_{self.data["colors"][0].upper()}_BUFF]'
