import json
import logging
import operator
import re

LOGLEVEL = logging.DEBUG

formatter = logging.Formatter('%(asctime)-15s [%(levelname)s] %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(LOGLEVEL)
log = logging.getLogger(__name__)

log.setLevel(LOGLEVEL)
log.addHandler(handler)

RARITIES = (
    'Common',
    'Uncommon',
    'Rare',
    'UltraRare',
    'Epic',
    'Mythic',
    'Doomed'
)

WEAPON_RARITIES = (
    'Common',
    'Uncommon',
    'Rare',
    'UltraRare',
    'Epic',
    'Mythic',
    'Doomed'
)


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


def extract_search_tag(search_term):
    ignored_characters = ' -\''
    for char in ignored_characters:
        search_term = search_term.replace(char, '')
    return search_term.lower()


class TeamExpander:
    FORMAT = re.compile(r'(en|fr|de|ru|it|es|cn)?-?\[(\d+,?){1,13}\]', re.IGNORECASE)
    COLORS = ('blue', 'green', 'red', 'yellow', 'purple', 'brown')

    def __init__(self):
        self.troops = {}
        self.spells = {}
        self.weapons = {}
        self.classes = {}
        self.banners = {}
        self.traits = {}
        self.kingdoms = {}
        self.pets = {}
        self.talent_trees = {}
        self.translations = Translations()
        self.populate_world_data()
        log.debug('Done populating world data.')

    def populate_world_data(self):
        with open('World.json', encoding='utf8') as f:
            data = json.load(f)

        for spell in data['Spells']:
            amount = 0
            multiplier = 1
            boost = 1
            for spell_step in spell['SpellSteps']:
                if spell_step.get('Primarypower'):
                    amount = spell_step.get('Amount')
                    multiplier = spell_step.get('SpellPowerMultiplier', 1)
                elif spell_step['Type'].startswith('Count'):
                    boost = spell_step.get('Amount', 1)
            self.spells[spell['Id']] = {
                'name': spell['Name'],
                'description': spell['Description'],
                'cost': spell['Cost'],
                'amount': amount,
                'multiplier': multiplier,
                'boost': boost,
            }
        for trait in data['Traits']:
            self.traits[trait['Code']] = {'name': trait['Name'], 'description': trait['Description']}
        for troop in data['Troops']:
            colors = [c.replace('Color', '').lower() for c, v in troop['ManaColors'].items() if v]
            self.troops[troop['Id']] = {
                'id': troop['Id'],
                'name': troop['Name'],
                'colors': sorted(colors),
                'description': troop['Description'],
                'spell_id': troop['SpellId'],
                'traits': [self.traits.get(trait, {'name': trait, 'description': '-'}) for trait in troop['Traits']],
                'rarity': troop['TroopRarity'],
                'types': [troop['TroopType']],
                'roles': troop['TroopRoleArray'],
                'kingdom': {'Name': ''},
            }
            if 'TroopType2' in troop:
                self.troops[troop['Id']]['types'].append(troop['TroopType2'])
        for kingdom in data['Kingdoms']:
            color_lookup_names = [f'[GEM_{c.upper()}]' for c in self.COLORS]
            color_names = [self.translations.get(c).lower() for c in color_lookup_names]
            colors = zip(color_names, kingdom['BannerColors'])
            colors = sorted(colors, key=operator.itemgetter(1), reverse=True)
            self.banners[kingdom['Id']] = {
                'name': kingdom['BannerName'],
                'colors': colors,
            }
            self.kingdoms[kingdom['Id']] = {
                'id': kingdom['Id'],
                'name': kingdom['Name'],
                'description': kingdom['Description'],
                'punchline': kingdom['ByLine'],
            }
            for troop_id in kingdom['TroopIds']:
                if troop_id != -1:
                    self.troops[troop_id]['kingdom'] = kingdom
        for weapon in data['Weapons']:
            colors = [c.replace('Color', '').lower() for c, v in weapon['ManaColors'].items() if v]
            self.weapons[weapon['Id']] = {
                'id': weapon['Id'],
                'name': f'[SPELL{weapon["SpellId"]}_NAME]',
                'description': f'[SPELL{weapon["SpellId"]}_DESC]',
                'colors': sorted(colors),
                'rarity': weapon['WeaponRarity'],
                'type': weapon['Type'],
                'roles': weapon['TroopRoleArray'],
                'spell_id': weapon['SpellId'],
                'kingdom': self.kingdoms[weapon['KingdomId']],
                'requirement': weapon['MasteryRequirement'],
            }
        for pet in data['Pets']:
            colors = [c.replace('Color', '').lower() for c, v in pet['ManaColors'].items() if v]
            self.pets[pet['Id']] = {
                'id': pet['Id'],
                'name': pet['Name'],
                'kingdom': self.kingdoms[pet['KingdomId']],
                'colors': sorted(colors),
            }
        for tree in data['TalentTrees']:
            talents = [self.traits.get(trait, trait) for trait in tree['Traits']]
            self.talent_trees[tree['Code']] = talents
        for _class in data['HeroClasses']:
            self.classes[_class['Id']] = {
                'id': _class['Id'],
                'name': _class['Name'],
                'talents': [self.talent_trees[tree] for tree in _class['TalentTrees']],
                'trees': _class['TalentTrees'],
                'traits': _class['Traits'],
                'weapon_id': _class['ClassWeaponId'],
                'kingdom_id': _class['KingdomId'],
                'type': _class['Augment'][0],
            }
            self.weapons[_class['ClassWeaponId']]['class'] = _class['Name']

    @classmethod
    def extract_code_from_message(cls, message):
        m = cls.FORMAT.search(message)
        if m is None:
            return None, None
        span = m.span()
        beginning = span[0] + message[span[0]:].find('[') + 1
        ending = span[1] - 1
        raw_code = message[beginning:ending]
        lang = 'en'
        if message[span[0]] != '[':
            lang = message[span[0]:span[0] + 2].lower()
        numbers = [int(n.strip()) for n in raw_code.split(',')]
        return numbers, lang

    def get_team_from_code(self, code, lang):
        result = {
            'troops': [],
            'banner': {},
            'class': None,
            'talents': [],
            'class_title': self.translations.get('[CLASS]', lang),
            'troops_title': self.translations.get('[TROOPS]', lang),
        }

        for element in code:
            troop = self.troops.get(element)
            weapon = self.weapons.get(element)
            if troop:
                color_code = "".join(troop["colors"])
                troop_name = self.translations.get(troop['name'], lang)
                result['troops'].append([color_code, troop_name])
                continue
            elif weapon:
                color_code = "".join(weapon["colors"])
                weapon_name = self.translations.get(weapon['name'], lang)
                result['troops'].append([color_code, weapon_name + ' :crossed_swords:'])
                continue

            _class = self.classes.get(element)
            if _class:
                result['class'] = self.translations.get(_class['name'], lang)
                result['class_talents'] = _class['talents']
                continue

            banner = self.banners.get(element)
            if banner:
                result['banner']['name'] = self.translations.get(banner['name'], lang)
                result['banner']['description'] = [c for c in banner['colors'] if c[1]]
                continue

            if 0 <= element <= 3:
                result['talents'].append(element)
                continue

        new_talents = []
        for talent_no, talent_code in enumerate(result['talents']):
            talent = '-'
            if talent_code > 0:
                talent = self.translations.get(result['class_talents'][talent_code - 1][talent_no]['name'], lang)
            new_talents.append(talent)
        result['talents'] = new_talents

        return result

    def get_team_from_message(self, message):
        code, lang = self.extract_code_from_message(message)
        if not code:
            return
        return self.get_team_from_code(code, lang)

    def search_troop(self, search_term, lang):
        if search_term.isdigit():
            result = self.troops.get(int(search_term)).copy()
            self.translate_troop(result, lang)
            return [result]
        else:
            possible_matches = []
            for troop in self.troops.values():
                translated_name = extract_search_tag(self.translations.get(troop['name'], lang))
                real_search = extract_search_tag(search_term)
                if real_search == translated_name:
                    result = troop.copy()
                    self.translate_troop(result, lang)
                    return [result]
                elif real_search in translated_name:
                    result = troop.copy()
                    self.translate_troop(result, lang)
                    possible_matches.append(result)
            return possible_matches

    def translate_troop(self, troop, lang):
        troop['name'] = self.translations.get(troop['name'], lang)
        troop['description'] = self.translations.get(troop['description'], lang)
        troop['color_code'] = "".join(troop['colors'])
        troop['rarity_title'] = self.translations.get('[RARITY]', lang)
        troop['raw_rarity'] = troop['rarity']
        rarity_number = 1
        if troop['rarity'] in RARITIES:
            rarity_number = RARITIES.index(troop['rarity'])
        troop['rarity'] = self.translations.get(f'[RARITY_{rarity_number}]', lang)
        troop['traits_title'] = self.translations.get('[TRAITS]', lang)
        traits = []
        for trait in troop['traits']:
            traits.append({
                'name': self.translations.get(trait['name'], lang),
                'description': self.translations.get(trait['description'], lang)
            })
        troop['traits'] = traits
        troop['roles_title'] = self.translations.get('[TROOP_ROLE]', lang)
        troop['roles'] = [self.translations.get(role, lang) for role in troop['roles']]
        troop['type_title'] = self.translations.get('[FILTER_TROOPTYPE]', lang)
        troop['raw_types'] = troop['types']
        types = [
            self.translations.get(f'[TROOPTYPE_{_type.upper()}]', lang) for _type in troop['types']
        ]
        troop['type'] = ' / '.join(types)
        troop['kingdom_title'] = self.translations.get('[KINGDOM]', lang)
        troop['kingdom'] = self.translations.get(troop['kingdom']['Name'], lang)
        troop['spell'] = self.translate_spell(troop['spell_id'], lang)
        troop['spell_title'] = self.translations.get('[TROOPHELP_SPELL0]', lang)

    def search_kingdom(self, search_term, lang):
        if search_term.isdigit():
            result = self.kingdoms.get(int(search_term)).copy()
            self.translate_kingdom(result, lang)
            return [result]
        else:
            possible_matches = []
            for kingdom in self.kingdoms.values():
                translated_name = extract_search_tag(self.translations.get(kingdom['name'], lang))
                real_search = extract_search_tag(search_term)
                if real_search == translated_name:
                    result = kingdom.copy()
                    self.translate_kingdom(result, lang)
                    return [result]
                elif real_search in translated_name:
                    result = kingdom.copy()
                    self.translate_kingdom(result, lang)
                    possible_matches.append(result)
            return possible_matches

    def translate_kingdom(self, kingdom, lang):
        kingdom['name'] = self.translations.get(kingdom['name'], lang)
        kingdom['description'] = self.translations.get(kingdom['description'], lang)
        kingdom['punchline'] = self.translations.get(kingdom['punchline'], lang)

    def search_class(self, search_term, lang):
        if search_term.isdigit():
            result = self.classes.get(int(search_term)).copy()
            self.translate_class(result, lang)
            return [result]
        else:
            possible_matches = []
            for _class in self.classes.values():
                translated_name = extract_search_tag(self.translations.get(_class['name'], lang))
                real_search = extract_search_tag(search_term)
                if real_search == translated_name:
                    result = _class.copy()
                    self.translate_class(result, lang)
                    return [result]
                elif real_search in translated_name:
                    result = _class.copy()
                    self.translate_class(result, lang)
                    possible_matches.append(result)
            return possible_matches

    def translate_class(self, _class, lang):
        kingdom = self.kingdoms[_class['kingdom_id']]
        _class['kingdom'] = self.translations.get(kingdom['name'], lang)
        weapon = self.weapons[_class['weapon_id']]
        _class['weapon'] = self.translations.get(weapon['name'], lang)
        _class['name'] = self.translations.get(_class['name'], lang)
        translated_trees = []
        for tree in _class['talents']:
            translated_talents = []
            for talent in tree:
                translated_talents.append({
                    'name': self.translations.get(talent['name'], lang),
                    'description': self.translations.get(talent['description'], lang)
                })
            translated_trees.append(translated_talents)
        _class['talents'] = translated_trees
        _class['trees'] = [self.translations.get(f'[TALENT_TREE_{t.upper()}]', lang) for t in _class['trees']]
        _class['type'] = self.translations.get(f'[PERK_TYPE_{_class["type"].upper()}]', lang)

    def search_pet(self, search_term, lang):
        if search_term.isdigit():
            result = self.pets.get(int(search_term)).copy()
            self.translate_pet(result, lang)
            return [result]
        else:
            possible_matches = []
            for pet in self.pets.values():
                translated_name = extract_search_tag(self.translations.get(pet['name'], lang))
                real_search = extract_search_tag(search_term)
                if real_search == translated_name:
                    result = pet.copy()
                    self.translate_pet(result, lang)
                    return [result]
                elif real_search in translated_name:
                    result = pet.copy()
                    self.translate_pet(result, lang)
                    possible_matches.append(result)
            return possible_matches

    def translate_pet(self, pet, lang):
        pet['name'] = self.translations.get(pet['name'], lang)
        pet['kingdom'] = self.translations.get(pet['kingdom']['name'], lang)
        pet['color_code'] = "".join(pet['colors'])

    def search_weapon(self, search_term, lang):
        if search_term.isdigit():
            result = self.weapons.get(int(search_term)).copy()
            self.translate_weapon(result, lang)
            return [result]
        else:
            possible_matches = []
            for weapon in self.weapons.values():
                translated_name = extract_search_tag(self.translations.get(weapon['name'], lang))
                real_search = extract_search_tag(search_term)
                if real_search == translated_name:
                    result = weapon.copy()
                    self.translate_weapon(result, lang)
                    return [result]
                elif real_search in translated_name:
                    result = weapon.copy()
                    self.translate_weapon(result, lang)
                    possible_matches.append(result)
            return possible_matches

    def translate_weapon(self, weapon, lang):
        weapon['name'] = self.translations.get(weapon['name'], lang)
        weapon['description'] = self.translations.get(weapon['description'], lang)
        weapon['color_code'] = "".join(weapon['colors'])
        weapon['spell_title'] = self.translations.get('[TROOPHELP_SPELL0]', lang)
        weapon['rarity_title'] = self.translations.get('[RARITY]', lang)
        weapon['raw_rarity'] = weapon['rarity']

        rarity_number = WEAPON_RARITIES.index(weapon['rarity'])
        weapon['rarity'] = self.translations.get(f'[RARITY_{rarity_number}]', lang)
        weapon['spell'] = self.translate_spell(weapon['spell_id'], lang)
        weapon['kingdom_title'] = self.translations.get('[KINGDOM]', lang)
        weapon['kingdom'] = self.translations.get(weapon['kingdom']['name'], lang)
        weapon['roles_title'] = self.translations.get('[WEAPON_ROLE]', lang)
        weapon['roles'] = [self.translations.get(f'[TROOP_ROLE_{role.upper()}]', lang) for role in weapon['roles']]
        weapon['type_title'] = self.translations.get('[FILTER_WEAPONTYPE]', lang)
        weapon['type'] = self.translations.get(f'[WEAPONTYPE_{weapon["type"].upper()}]', lang)
        if weapon['requirement'] < 1000:
            weapon['requirement_text'] = self.translations.get('[WEAPON_MASTERY_REQUIRED]', lang) + \
                                         str(weapon['requirement'])
        elif weapon['requirement'] == 1000:
            weapon['requirement_text'] = self.translations.get('[WEAPON_AVAILABLE_FROM_CHESTS_AND_EVENTS]', lang)
        elif weapon['requirement'] == 1002:
            _class = self.translations.get(weapon['class'], lang)
            weapon['requirement_text'] = self.translations.get('[CLASS_REWARD_TITLE]', lang) + f' ({_class})'
        elif weapon['requirement'] == 1003:
            weapon['requirement_text'] = self.translations.get('[SOULFORGE_WEAPONS_TAB_EMPTY_ERROR]', lang)

    def translate_spell(self, spell_id, lang):
        spell = self.spells[spell_id]
        magic = self.translations.get('[MAGIC]', lang)
        spell_amount = ''
        if spell['amount']:
            spell_amount = f' + {spell["amount"]}'
        multiplier = ''
        if spell['multiplier'] > 1:
            multiplier = f'{int(spell["multiplier"])} ⨯ '
        divisor = ''
        if spell['multiplier'] < 1:
            number = int(round(1 / spell['multiplier']))
            divisor = f' / {number}'
        boost = ''
        if spell['boost'] > 100:
            boost = f' [x{int(round(spell["boost"]/100))}]'
        elif spell['boost'] != 1 and spell['boost'] <= 100:
            boost = f' [{int(round(1/(spell["boost"]/100)))}:1]'
        damage = f'[{multiplier}{magic}{divisor}{spell_amount}]'
        description = self.translations.get(spell['description'], lang).replace('{1}', damage) + boost
        return {
            'name': self.translations.get(spell['name'], lang),
            'cost': spell['cost'],
            'description': description,
        }
