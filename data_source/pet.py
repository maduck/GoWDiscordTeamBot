from data_source.base_game_data import BaseGameData, BaseGameDataContainer
from util import convert_color_array

EFFECT_TRANSLATIONS = (
    '[PETTYPE_BUFFTEAMCOLOR]',
    '[PETTYPE_BUFFGEMMASTERY]',
    '[PETTYPE_BUFFTEAMKINGDOM]',
    '[PETTYPE_BUFFTEAMTROOPTYPE]',
    '[PETTYPE_LOOTSOULS]',
    '[PETTYPE_LOOTGOLD]',
    '[PETTYPE_LOOTXP]',
    '[PETTYPE_NOEFFECT]',
    '[PETTYPE_BONUSGNOMECHANCE]',
    '[PETTYPE_BONUSMAPTURNS]',
    '[PETTYPE_BUFFSINGLETROOP]',
)


class Pet(BaseGameData):
    def set_effect_data(self, value):
        self.data['effect_data'] = value


class PetContainer(BaseGameDataContainer):
    DATA_CLASS = Pet
    LOOKUP_KEYS = ['name', 'kingdom_name']
    EFFECT_BONUS = {}
    user_data = {}
    world_data = {}

    def __init__(self, data, user_data, world_data):
        super().__init__()
        self.user_data = user_data
        self.world_data = world_data
        self.data = {
            'id': data['Id'],
            'name': data['Name'],
            'colors': convert_color_array(data),
            'color_code': ''.join(convert_color_array(data)),
            'effect': EFFECT_TRANSLATIONS[data.get('Effect', 0)],
            'effect_data': data.get('EffectData'),
            'effect_title': '[BONUS]',
            'troop_type': data.get('EffectTroopType'),
            'reference_name': data['ReferenceName'],
            'filename': data['FileBase'],
            'kingdom_id': data['KingdomId'],
            'kingdom_name': f'[{data["KingdomId"]}_NAME]',
            'kingdom_title': '[KINGDOM]',
            'region_title': '[REGION_BONUS]',
            'region_sentence': '[PVP_BONUS_REGION_N]',
            'region_id': data.get('RegionId'),
            'region_name': f'[PVP_REGION_{data.get("RegionId")}]' if data.get('RegionId') else '',
        }
        self.populate_effect_data()
        self.translate()

    def populate_effect_data(self):
        effect = self.data['effect']

        if not self.EFFECT_BONUS:
            self.get_effect_bonuses()
        effect_levels = self.EFFECT_BONUS.get(effect, [])

        if effect == '[PETTYPE_BUFFTEAMCOLOR]':
            self.data['effect_data'] = None
            self.data['effect'] = '[PET_TEAM_BONUS]'
            self.data['effect_replacement'] = {
                '%1': '/'.join([f'`{b}`' for b in effect_levels]),
                '%2': f'[{self.data["color_code"].upper()}]',
            }
        elif effect == '[PETTYPE_BUFFGEMMASTERY]':
            self.data['effect_data'] = None
            self.data['effect'] = '[PET_MASTERY_BONUS]'
            self.data['effect_replacement'] = {
                '%1': '/'.join([f'`{b}`' for b in effect_levels]),
                '%2': f'[{self.data["color_code"].upper()}]',
            }
        elif effect == '[PETTYPE_BUFFTEAMKINGDOM]':
            self.data['effect'] = '[PET_TEAM_BONUS]'
            self.data['effect_replacement'] = {
                '%1': '/'.join([f'`{b}`' for b in effect_levels]),
                '%2': f'[{self.data["effect_data"]}_NAME]',
            }
            self.data['effect_data'] = None
        elif effect == '[PETTYPE_BUFFTEAMTROOPTYPE]':
            troop_type = self.data['troop_type'].upper()
            self.data['effect'] = '[PET_TEAM_BONUS]'
            self.data['effect_replacement'] = {
                '%1': '/'.join([f'`{b}`' for b in effect_levels]),
                '%2': f'[TROOPTYPE_{troop_type}]',
            }
            self.data['effect_data'] = None
        elif effect == '[PETTYPE_LOOTGOLD]':
            self.data['effect'] = '[PET_LOOT_BONUS]'
            self.data['effect_replacement'] = {
                '%1': '/'.join([f'`{b}`' for b in effect_levels]),
                '%2': '[GOLD]',
            }
        elif effect == '[PETTYPE_LOOTSOULS]':
            self.data['effect'] = '[PET_LOOT_BONUS]'
            self.data['effect_replacement'] = {
                '%1': '/'.join([f'`{b}`' for b in effect_levels]),
                '%2': '[SOULS]',
            }
        elif effect == '[PETTYPE_LOOTXP]':
            self.data['effect'] = '[PET_LOOT_BONUS]'
            self.data['effect_replacement'] = {
                '%1': '/'.join([f'`{b}`' for b in effect_levels]),
                '%2': '[XP]',
            }
        elif effect == '[PETTYPE_BONUSGNOMECHANCE]':
            self.data['effect'] = '[PET_GNOME_BONUS]'
            self.data['effect_replacement'] = {
                '%1': '/'.join([f'`{100 * b}`' for b in effect_levels]),
            }
        elif effect == '[PETTYPE_BONUSMAPTURNS]':
            self.data['effect'] = '[PET_MAPTURNS_BONUS]'
            self.data['effect_replacement'] = {
                '%1': '/'.join([f'`{b}`' for b in effect_levels]),
            }
        elif effect == '[PETTYPE_NOEFFECT]':
            self.data['effect'] = '[PET_NO_BONUS]'
            self.data['effect_data'] = '[PET_BONUS_DESCRIPTION_EVENT]'
        elif effect == '[PETTYPE_BUFFSINGLETROOP]':
            troop = self.world_data.get(self.data['effect_data'], {}).get('name')
            self.data['effect'] = '[PET_SINGLE_TROOP_BONUS_DESC]'
            self.data['effect_replacement'] = {
                '%1': '',
                '%2': troop,
            }
            self.data['effect_data'] = ''

    def get_effect_bonuses(self):
        for bonus in self.user_data['pEconomyModel']['PetEffects']:
            bonus_name = f'[PETTYPE_{bonus["EffectName"].upper()}]'
            self.EFFECT_BONUS[bonus_name] = bonus['Bonuses']

    def translate(self):
        super().translate()
        for translation in self.translations.values():
            if 'effect_replacement' in translation:
                for before, after in translation.data['effect_replacement'].items():
                    if after is None:
                        after = ''
                    translation.data['effect'] = translation.data['effect'].replace(before, after)

    def fill_untranslated_kingdom_name(self, kingdom_id, kingdom_reference_name):
        super().fill_untranslated_kingdom_name(kingdom_id, kingdom_reference_name)
        if self.data['effect'] == '[PETTYPE_BUFFTEAMKINGDOM]' \
                and self.is_untranslated(self.translations['en'].effect_data) \
                and str(kingdom_id) in self.translations['en'].effect_data:
            for pet in self.translations.values():
                pet.set_effect_data(kingdom_reference_name)

    def __repr__(self):
        return f'<{self.data["filename"]} id={self.data["id"]} name={self.data["reference_name"]!r} ' \
               f'kingdom_id={self.data["kingdom_id"]}>'
