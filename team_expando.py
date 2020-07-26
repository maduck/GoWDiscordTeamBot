import json
import logging
import operator
import re

from translations import _

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
        self.pet_effects = ()
        self.pets = {}
        self.talent_trees = {}
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
                'id': spell['Id'],
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
                'filename': f'http://garyatrics.com/gow_assets/{troop["FileBase"].lower()}.png',
            }
            if 'TroopType2' in troop:
                self.troops[troop['Id']]['types'].append(troop['TroopType2'])
        for kingdom in data['Kingdoms']:
            color_lookup_names = [f'[GEM_{c.upper()}]' for c in self.COLORS]
            color_names = [_(c).lower() for c in color_lookup_names]
            colors = zip(color_names, kingdom['BannerColors'])
            colors = sorted(colors, key=operator.itemgetter(1), reverse=True)
            self.banners[kingdom['Id']] = {
                'name': kingdom['BannerName'],
                'colors': colors,
            }
            kingdom_troops = [troop_id for troop_id in kingdom['TroopIds'] if troop_id != -1]
            self.kingdoms[kingdom['Id']] = {
                'id': kingdom['Id'],
                'name': kingdom['Name'],
                'description': kingdom['Description'],
                'punchline': kingdom['ByLine'],
                'underworld': bool(kingdom.get('MapIndex', 0)),
                'troop_ids': kingdom_troops,
                'troop_type': kingdom['KingdomTroopType'],
                'linked_kingdom_id': kingdom.get('SisterKingdomId'),
            }
            if 'SisterKingdomId' in kingdom:
                self.kingdoms[kingdom['SisterKingdomId']]['linked_kingdom_id'] = kingdom['Id']
            for troop_id in kingdom_troops:
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
                'affixes': [self.spells.get(spell) for spell in weapon['Affixes'] if spell in self.spells],
            }
        self.pet_effects = (
            '[PETTYPE_BUFFTEAMCOLOR]',
            '[PETTYPE_BUFFGEMMASTERY]',
            '[PETTYPE_BUFFTEAMKINGDOM]',
            '[PETTYPE_BUFFTEAMTROOPTYPE]',
            '[PETTYPE_LOOTSOULS]',
            '[PETTYPE_LOOTGOLD]',
            '[PETTYPE_LOOTXP]',
            '[PETTYPE_NOEFFECT]',
        )
        for pet in data['Pets']:
            colors = [c.replace('Color', '').lower() for c, v in pet['ManaColors'].items() if v]
            self.pets[pet['Id']] = {
                'id': pet['Id'],
                'name': pet['Name'],
                'kingdom': self.kingdoms[pet['KingdomId']],
                'colors': sorted(colors),
                'effect': self.pet_effects[pet['Effect']],
                'effect_data': pet.get('EffectData'),
                'troop_type': pet.get('EffectTroopType'),
            }
        for tree in data['TalentTrees']:
            talents = [self.traits.get(trait, trait) for trait in tree['Traits']]
            self.talent_trees[tree['Code']] = {
                'name': f'[TALENT_TREE_{tree["Code"].upper()}]',
                'talents': talents,
                'classes': [],
            }
        for _class in data['HeroClasses']:
            self.classes[_class['Id']] = {
                'id': _class['Id'],
                'name': _class['Name'],
                'talents': [self.talent_trees[tree]['talents'] for tree in _class['TalentTrees']],
                'trees': _class['TalentTrees'],
                'traits': [self.traits.get(trait, {'name': trait, 'description': '-'}) for trait in _class['Traits']],
                'weapon_id': _class['ClassWeaponId'],
                'kingdom_id': _class['KingdomId'],
                'type': _class['Augment'][0],
            }
            self.weapons[_class['ClassWeaponId']]['class'] = _class['Name']
            for tree in _class['TalentTrees']:
                self.talent_trees[tree]['classes'].append(self.classes[_class['Id']].copy())

    @classmethod
    def extract_code_from_message(cls, raw_code):
        numbers = [int(n.strip()) for n in raw_code.split(',') if n]
        return numbers

    def get_team_from_code(self, code, lang):
        result = {
            'troops': [],
            'banner': {},
            'class': None,
            'talents': [],
            'class_title': _('[CLASS]', lang),
            'troops_title': _('[TROOPS]', lang),
        }
        has_weapon = False

        for element in code:
            troop = self.troops.get(element)
            weapon = self.weapons.get(element)
            if troop:
                color_code = "".join(troop["colors"])
                troop_name = _(troop['name'], lang)
                result['troops'].append([color_code, troop_name])
                continue
            elif weapon:
                color_code = "".join(weapon["colors"])
                weapon_name = _(weapon['name'], lang)
                result['troops'].append([color_code, weapon_name + ' :crossed_swords:'])
                has_weapon = True
                continue

            _class = self.classes.get(element)
            if _class:
                result['class'] = _(_class['name'], lang)
                result['class_talents'] = _class['talents']
                continue

            banner = self.banners.get(element)
            if banner:
                result['banner']['name'] = _(banner['name'], lang)
                result['banner']['description'] = [c for c in banner['colors'] if c[1]]
                continue

            if 0 <= element <= 3:
                result['talents'].append(element)
                continue

        if has_weapon:
            new_talents = []
            for talent_no, talent_code in enumerate(result['talents']):
                talent = '-'
                if talent_code > 0:
                    talent = _(result['class_talents'][talent_code - 1][talent_no]['name'], lang)
                new_talents.append(talent)
            result['talents'] = new_talents
        else:
            result['class'] = None
            result['talents'] = None

        return result

    def get_team_from_message(self, user_code, lang):
        code = self.extract_code_from_message(user_code)
        if not code:
            return
        return self.get_team_from_code(code, lang)

    def search_troop(self, search_term, lang):
        if search_term.isdigit() and int(search_term) in self.troops:
            troop = self.troops.get(int(search_term))
            if troop:
                result = troop.copy()
                self.translate_troop(result, lang)
                return [result]
            return []
        else:
            possible_matches = []
            for troop in self.troops.values():
                translated_name = extract_search_tag(_(troop['name'], lang))
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
        troop['name'] = _(troop['name'], lang)
        troop['description'] = _(troop['description'], lang).replace('widerbeleben',
                                                                                         'wiederbeleben')
        troop['color_code'] = "".join(troop['colors'])
        troop['rarity_title'] = _('[RARITY]', lang)
        troop['raw_rarity'] = troop['rarity']
        rarity_number = 1
        if troop['rarity'] in RARITIES:
            rarity_number = RARITIES.index(troop['rarity'])
        troop['rarity'] = _(f'[RARITY_{rarity_number}]', lang)
        troop['traits_title'] = _('[TRAITS]', lang)
        troop['traits'] = self.enrich_traits(troop['traits'], lang)
        troop['roles_title'] = _('[TROOP_ROLE]', lang)
        troop['roles'] = [_(f'[TROOP_ROLE_{role.upper()}]', lang) for role in troop['roles']]
        troop['type_title'] = _('[FILTER_TROOPTYPE]', lang)
        troop['raw_types'] = troop['types']
        types = [
            _(f'[TROOPTYPE_{_type.upper()}]', lang) for _type in troop['types']
        ]
        troop['type'] = ' / '.join(types)
        troop['kingdom_title'] = _('[KINGDOM]', lang)
        troop['kingdom'] = _(troop['kingdom']['Name'], lang)
        troop['spell'] = self.translate_spell(troop['spell_id'], lang)
        troop['spell_title'] = _('[TROOPHELP_SPELL0]', lang)

    def enrich_traits(self, traits, lang):
        new_traits = []
        for trait in traits:
            new_traits.append({
                'name': _(trait['name'], lang),
                'description': _(trait['description'], lang)
            })
        return new_traits

    def search_kingdom(self, search_term, lang):
        if search_term.isdigit() and int(search_term) in self.kingdoms:
            result = self.kingdoms.get(int(search_term)).copy()
            self.translate_kingdom(result, lang)
            return [result]
        else:
            possible_matches = []
            for kingdom in self.kingdoms.values():
                translated_name = extract_search_tag(_(kingdom['name'], lang))
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
        kingdom['name'] = _(kingdom['name'], lang)
        kingdom['description'] = _(kingdom['description'], lang)
        kingdom['punchline'] = _(kingdom['punchline'], lang)
        kingdom['troop_title'] = _('[TROOPS]', lang)
        kingdom['troops'] = [
            {'name': _(self.troops[_id]['name'], lang),
             'id': _id
             } for _id in kingdom['troop_ids']
        ]
        kingdom['linked_kingdom'] = None
        if kingdom['linked_kingdom_id']:
            kingdom['linked_kingdom'] = _(self.kingdoms[kingdom['linked_kingdom_id']]['name'], lang)
        if kingdom['linked_kingdom'].startswith('['):
            kingdom['linked_kingdom'] = None
        kingdom['map'] = _('[MAPNAME_MAIN]', lang)
        kingdom['linked_map'] = _('[MAPNAME_UNDERWORLD]', lang)
        if kingdom['underworld']:
            kingdom['map'] = _('[MAPNAME_UNDERWORLD]', lang)
            kingdom['linked_map'] = _('[MAPNAME_MAIN]', lang)

    def search_class(self, search_term, lang):
        if search_term.isdigit() and int(search_term) in self.classes:
            result = self.classes.get(int(search_term)).copy()
            self.translate_class(result, lang)
            return [result]
        else:
            possible_matches = []
            for _class in self.classes.values():
                translated_name = extract_search_tag(_(_class['name'], lang))
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
        _class['kingdom'] = _(kingdom['name'], lang)
        weapon = self.weapons[_class['weapon_id']]
        _class['weapon'] = _(weapon['name'], lang)
        _class['name'] = _(_class['name'], lang)
        translated_trees = []
        for tree in _class['talents']:
            translated_talents = []
            for talent in tree:
                translated_talents.append({
                    'name': _(talent['name'], lang),
                    'description': _(talent['description'], lang)
                })
            translated_trees.append(translated_talents)
        _class['kingdom_title'] = _('[KINGDOM]', lang)
        _class['traits_title'] = _('[TRAITS]', lang)
        _class['traits'] = self.enrich_traits(_class['traits'], lang)
        _class['weapon_title'] = _('[WEAPON]', lang)
        _class['talents'] = translated_trees
        _class['trees'] = [_(f'[TALENT_TREE_{t.upper()}]', lang) for t in _class['trees']]
        _class['type'] = _(f'[PERK_TYPE_{_class["type"].upper()}]', lang)

    def search_talent_tree(self, search_term, lang):
        possible_matches = []
        for tree in self.talent_trees.values():
            translated_name = extract_search_tag(_(tree['name'], lang))
            translated_talents = [_(t['name'], lang) for t in tree['talents']]
            real_search = extract_search_tag(search_term)
            if real_search == translated_name or real_search in translated_talents:
                result = tree.copy()
                self.translate_talent_tree(result, lang)
                return [result]
            elif real_search in translated_name:
                result = tree.copy()
                self.translate_talent_tree(result, lang)
                possible_matches.append(result)
            else:
                talent_matches = [t for t in translated_talents if real_search in extract_search_tag(t)]
                if talent_matches:
                    result = tree.copy()
                    result['talent_matches'] = talent_matches
                    self.translate_talent_tree(result, lang)
                    possible_matches.append(result)
        return possible_matches

    def translate_talent_tree(self, tree, lang):
        tree['name'] = _(tree['name'], lang)
        translated_talents = []
        for talent in tree['talents']:
            translated_talents.append({
                'name': _(talent['name'], lang),
                'description': _(talent['description'], lang)
            })
        tree['talents'] = translated_talents
        tree['classes'] = [
            {'id': c['id'],
             'name': _(c['name'], lang)
             }
            for c in tree['classes']
        ]

    def search_pet(self, search_term, lang):
        if search_term.isdigit() and int(search_term) in self.pets:
            result = self.pets.get(int(search_term)).copy()
            self.translate_pet(result, lang)
            return [result]
        else:
            possible_matches = []
            for pet in self.pets.values():
                translated_name = extract_search_tag(_(pet['name'], lang))
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
        pet['name'] = _(pet['name'], lang)
        pet['kingdom'] = _(pet['kingdom']['name'], lang)
        pet['kingdom_title'] = _('[KINGDOM]', lang)
        pet['color_code'] = "".join(pet['colors'])
        pet['raw_effect'] = pet['effect']
        pet['effect'] = _(pet['effect'], lang)
        colors = (
            '',
            'GREEN',
            'RED',
            'YELLOW',
            'PURPLE',
            'BROWN',
        )
        if pet['raw_effect'] == '[PETTYPE_BUFFTEAMKINGDOM]':
            pet['effect_data'] = _(self.kingdoms[pet['effect_data']]['name'], lang)
        elif pet['raw_effect'] == '[PETTYPE_BUFFTEAMTROOPTYPE]':
            pet['effect_data'] = _(f'[TROOPTYPE_{pet["troop_type"].upper()}]', lang)
        elif pet['raw_effect'] == '[PETTYPE_BUFFTEAMCOLOR]':
            pet['effect'] = _(f'[PET_{pet["colors"][0].upper()}_BUFF]', lang)
            pet['effect_data'] = None
        elif pet['raw_effect'] == '[PETTYPE_BUFFGEMMASTERY]':
            if pet['effect_data']:
                pet['effect'] = _(f'[PET_{colors[pet["effect_data"]]}_BUFF]', lang)
                pet['effect_data'] = None
            else:
                pet['effect'] = _(f'[PET_{pet["colors"][0].upper()}_BUFF]', lang)
        pet['effect_title'] = _('[PET_TYPE]', lang)

    def search_weapon(self, search_term, lang):
        if search_term.isdigit() and int(search_term) in self.weapons:
            weapon = self.weapons.get(int(search_term))
            if weapon:
                result = weapon.copy()
                self.translate_weapon(result, lang)
                return [result]
            return []
        else:
            possible_matches = []
            for weapon in self.weapons.values():
                translated_name = extract_search_tag(_(weapon['name'], lang))
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
        weapon['name'] = _(weapon['name'], lang)
        weapon['description'] = _(weapon['description'], lang)
        weapon['color_code'] = "".join(weapon['colors'])
        weapon['spell_title'] = _('[TROOPHELP_SPELL0]', lang)
        weapon['rarity_title'] = _('[RARITY]', lang)
        weapon['raw_rarity'] = weapon['rarity']

        rarity_number = WEAPON_RARITIES.index(weapon['rarity'])
        weapon['rarity'] = _(f'[RARITY_{rarity_number}]', lang)
        weapon['spell'] = self.translate_spell(weapon['spell_id'], lang)
        weapon['affix_title'] = _('[UPGRADE_WEAPON]', lang)
        weapon['affixes'] = [self.translate_spell(spell['id'], lang) for spell in weapon['affixes']]
        weapon['kingdom_title'] = _('[KINGDOM]', lang)
        weapon['kingdom'] = _(weapon['kingdom']['name'], lang)
        weapon['roles_title'] = _('[WEAPON_ROLE]', lang)
        weapon['roles'] = [_(f'[TROOP_ROLE_{role.upper()}]', lang) for role in weapon['roles']]
        weapon['type_title'] = _('[FILTER_WEAPONTYPE]', lang)
        weapon['type'] = _(f'[WEAPONTYPE_{weapon["type"].upper()}]', lang)
        if weapon['requirement'] < 1000:
            weapon['requirement_text'] = _('[WEAPON_MASTERY_REQUIRED]', lang) + \
                                         str(weapon['requirement'])
        elif weapon['requirement'] == 1000:
            weapon['requirement_text'] = _('[WEAPON_AVAILABLE_FROM_CHESTS_AND_EVENTS]', lang)
        elif weapon['requirement'] == 1002:
            _class = _(weapon['class'], lang)
            weapon['requirement_text'] = _('[CLASS_REWARD_TITLE]', lang) + f' ({_class})'
        elif weapon['requirement'] == 1003:
            weapon['requirement_text'] = _('[SOULFORGE_WEAPONS_TAB_EMPTY_ERROR]', lang)

    def translate_spell(self, spell_id, lang):
        spell = self.spells[spell_id]
        magic = _('[MAGIC]', lang)
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
            boost = f' [x{int(round(spell["boost"] / 100))}]'
        elif spell['boost'] != 1 and spell['boost'] <= 100:
            boost = f' [{int(round(1 / (spell["boost"] / 100)))}:1]'
        damage = f'[{multiplier}{magic}{divisor}{spell_amount}]'
        description = _(spell['description'], lang).replace('{1}', damage) + boost
        return {
            'name': _(spell['name'], lang),
            'cost': spell['cost'],
            'description': description,
        }
