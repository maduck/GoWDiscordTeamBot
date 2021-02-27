from data_source.base_game_data import BaseGameData
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
    LOOKUP_KEYS = ['name', 'kingdom']

    def __init__(self, data):
        super().__init__()
        self.raw_data = {
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
        effect = self.raw_data['effect']
        if effect == '[PETTYPE_BUFFTEAMKINGDOM]':
            self.raw_data['effect_data'] = f'[{self.raw_data["effect_data"]}_NAME]'
        elif effect == '[PETTYPE_BUFFTEAMTROOPTYPE]':
            troop_type = self.raw_data['troop_type'].upper()
            self.raw_data['effect_data'] = f'[TROOPTYPE_{troop_type}]'
        elif effect == '[PETTYPE_BUFFTEAMCOLOR]':
            color = self.raw_data['colors'][0].upper()
            self.raw_data['effect'] = f'[PET_{color}_BUFF]'
            self.raw_data['effect_data'] = None
        elif effect == '[PETTYPE_BUFFGEMMASTERY]':
            if self.raw_data['effect_data']:
                color = COLORS[self.raw_data['effect_data']].upper()
                self.raw_data['effect'] = f'[PET_{color}_BUFF]'
                self.raw_data['effect_data'] = None
            else:
                self.raw_data['effect'] = f'[PET_{self.raw_data["colors"][0].upper()}_BUFF]'
