import datetime
import importlib
import logging

import translations
from data_source.game_data import GameData
from game_constants import TROOP_RARITIES, WEAPON_RARITIES

LOGLEVEL = logging.DEBUG

formatter = logging.Formatter('%(asctime)-15s [%(levelname)s] %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(LOGLEVEL)
log = logging.getLogger(__name__)

log.setLevel(LOGLEVEL)
log.addHandler(handler)

_ = translations.Translations().get


def update_translations():
    global _
    importlib.reload(translations)
    del _
    _ = translations.Translations().get


def extract_search_tag(search_term):
    ignored_characters = ' -\'’'
    for char in ignored_characters:
        search_term = search_term.replace(char, '')
    return search_term.lower()


class TeamExpander:

    def __init__(self):
        world = GameData()
        world.populate_world_data()
        self.troops = world.troops
        self.spells = world.spells
        self.weapons = world.weapons
        self.classes = world.classes
        self.banners = world.banners
        self.traits = world.traits
        self.kingdoms = world.kingdoms
        self.pet_effects = world.pet_effects
        self.pets = world.pets
        self.talent_trees = world.talent_trees
        self.spoilers = world.spoilers
        self.events = world.events
        self.colors = world.COLORS
        self.campaign_tasks = world.campaign_tasks
        self.rooms = {}

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
        has_class = False

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
                has_class = True
                continue

            banner = self.banners.get(element)
            if banner:
                result['banner'] = self.translate_banner(banner, lang)
                continue

            if 0 <= element <= 3:
                result['talents'].append(element)
                continue

        if has_weapon and has_class:
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
        if troop['rarity'] in TROOP_RARITIES:
            rarity_number = TROOP_RARITIES.index(troop['rarity'])
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
            name_to_translate = trait['name']
            if name_to_translate == 'none':
                name_to_translate = '[NONE]'
            new_traits.append({
                'name': _(name_to_translate, lang),
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
                elif real_search in translated_name or \
                        (search_term == 'summary' and not kingdom['underworld'] and len(kingdom['colors']) > 0):
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
        kingdom['banner_title'] = _('[BANNERS]', lang)
        kingdom['banner'] = self.translate_banner(self.banners[kingdom['id']], lang)

        kingdom['linked_kingdom'] = None
        if kingdom['linked_kingdom_id']:
            kingdom['linked_kingdom'] = _(self.kingdoms[kingdom['linked_kingdom_id']]['name'], lang)
        if kingdom['linked_kingdom'] and kingdom['linked_kingdom'].startswith('['):
            kingdom['linked_kingdom'] = None
        kingdom['map'] = _('[MAPNAME_MAIN]', lang)
        kingdom['linked_map'] = _('[MAPNAME_UNDERWORLD]', lang)
        if kingdom['underworld']:
            kingdom['map'] = _('[MAPNAME_UNDERWORLD]', lang)
            kingdom['linked_map'] = _('[MAPNAME_MAIN]', lang)
        if 'primary_color' in kingdom:
            deed_num = self.colors.index(kingdom['primary_color'])
            kingdom['deed'] = _(f'[DEED{deed_num:02d}]', lang)
        kingdom['color_title'] = _('[GEM_MASTERY]', lang)
        kingdom['stat_title'] = _('[STAT_BONUS]', lang)
        if 'primary_stat' in kingdom:
            kingdom['primary_stat'] = _(f'[{kingdom["primary_stat"].upper()}]', lang)
        if 'pet' in kingdom:
            kingdom['pet_title'] = _('[PET_RESCUE_PET]', lang)
            pet = kingdom['pet'].copy()
            self.translate_pet(pet, lang)
            kingdom['pet'] = pet

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
                elif real_search in translated_name or search_term == 'summary':
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
        _class['talents_title'] = _('[TALENT_TREES]', lang)
        _class['kingdom_title'] = _('[KINGDOM]', lang)
        _class['traits_title'] = _('[TRAITS]', lang)
        _class['traits'] = self.enrich_traits(_class['traits'], lang)
        _class['weapon_title'] = _('[WEAPON]', lang)
        _class['talents'] = translated_trees
        _class['trees'] = [_(f'[TALENT_TREE_{t.upper()}]', lang) for t in _class['trees']]
        _class['type_short'] = _(f'[TROOPTYPE_{_class["type"].upper()}]', lang)
        _class['type'] = _(f'[PERK_TYPE_{_class["type"].upper()}]', lang)

    def search_talent_tree(self, search_term, lang):
        possible_matches = []
        for tree in self.talent_trees.values():
            translated_name = extract_search_tag(_(tree['name'], lang))
            translated_talents = [_(t['name'], lang) for t in tree['talents']]
            talents_search_tags = [extract_search_tag(t) for t in translated_talents]
            real_search = extract_search_tag(search_term)
            if real_search == translated_name or real_search in talents_search_tags:
                result = tree.copy()
                self.translate_talent_tree(result, lang)
                return [result]
            elif real_search in translated_name:
                result = tree.copy()
                self.translate_talent_tree(result, lang)
                possible_matches.append(result)
            else:
                talent_matches = [t for t in talents_search_tags if real_search in t]
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
        weapon['upgrade_title'] = _('[UPGRADE_WEAPON]', lang)

        bonus_title = _('[BONUS]', lang)
        upgrade_numbers = zip(weapon['armor_increase'], weapon['attack_increase'], weapon['health_increase'],
                              weapon['magic_increase'])
        upgrade_titles = (
            _('[ARMOR]', lang),
            _('[ATTACK]', lang),
            _('[LIFE]', lang),
            _('[MAGIC]', lang),
        )
        upgrades = []
        for upgrade in upgrade_numbers:
            for i, amount in enumerate(upgrade):
                if amount:
                    upgrades.append(
                        {'name': f'{upgrade_titles[i]} {bonus_title}',
                         'description': f'+{amount} {upgrade_titles[i]}'})

        weapon['upgrades'] = upgrades + [self.translate_spell(spell['id'], lang) for spell in weapon['affixes']]
        weapon['kingdom_title'] = _('[KINGDOM]', lang)
        weapon['kingdom'] = _(weapon['kingdom']['name'], lang)
        weapon['roles_title'] = _('[WEAPON_ROLE]', lang)
        weapon['roles'] = [_(f'[TROOP_ROLE_{role.upper()}]', lang) for role in weapon['roles']]
        weapon['type_title'] = _('[FILTER_WEAPONTYPE]', lang)
        weapon['type'] = _(f'[WEAPONTYPE_{weapon["type"].upper()}]', lang)

        weapon['has_mastery_requirement_color'] = False
        if weapon['requirement'] < 1000:
            weapon['requirement_text'] = _('[WEAPON_MASTERY_REQUIRED]', lang) + \
                                         str(weapon['requirement'])
            weapon['has_mastery_requirement_color'] = True
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

        description = _(spell['description'], lang)

        for i, (multiplier, amount) in enumerate(spell['effects'], start=1):
            spell_amount = f' + {amount}' if amount else ''
            multiplier_text = ''
            if multiplier > 1:
                if multiplier == int(multiplier):
                    multiplier_text = f'{multiplier:.0f} ⨯ '
                else:
                    multiplier_text = f'{multiplier} ⨯ '
            divisor = ''
            if multiplier < 1:
                number = int(round(1 / multiplier))
                divisor = f' / {number}'
            damage = f'[{multiplier_text}{magic}{divisor}{spell_amount}]'
            if '{2}' in description and len(spell['effects']) == 1:
                multiplier *= 0.5
                amount *= 0.5
                if amount == int(amount):
                    amount = int(amount)
                half_damage = f'[{multiplier} ⨯ {magic}{divisor} + {amount}]'
                description = description.replace('{1}', half_damage)
                description = description.replace('{2}', damage)
            else:
                description = description.replace(f'{{{i}}}', damage)

        boost = ''
        if spell['boost'] and spell['boost'] > 100:
            boost = f' [x{int(round(spell["boost"] / 100))}]'
        elif spell['boost'] and spell['boost'] != 1 and spell['boost'] <= 100:
            boost = f' [{int(round(1 / (spell["boost"] / 100)))}:1]'

        description = f'{description}{boost}'

        return {
            'name': _(spell['name'], lang),
            'cost': spell['cost'],
            'description': description,
        }

    @staticmethod
    def translate_banner(banner, lang):
        result = {
            'name': _(banner['name'], lang),
            'colors': [(_(c[0], 'en').lower(), c[1]) for c in banner['colors'] if c[1]],
            'filename': banner['filename'],
        }
        return result

    def get_events(self, lang):
        today = datetime.date.today()
        events = [self.translate_event(e, lang) for e in self.events if today <= e['start']]
        return events

    def translate_event(self, event, lang):
        entry = event.copy()

        entry['extra_info'] = ''
        if entry['type'] in ('[BOUNTY]', '[HIJACK]') and entry['gacha']:
            entry['extra_info'] = _(self.troops[entry['gacha']]['name'], lang)
        elif entry['type'] == '[PETRESCUE]' and entry['gacha']:
            entry['extra_info'] = _(self.pets[entry['gacha']]['name'], lang)
        elif entry['type'] == '[CLASS_EVENT]' and entry['gacha']:
            entry['extra_info'] = _(self.classes[entry['gacha']]['name'], lang)
        elif entry['type'] == '[DELVE_EVENT]':
            entry['extra_info'] = _(self.kingdoms[entry['kingdom_id']]['name'], lang)
        elif entry['type'] in ('[INVASION]', '[ADVENTURE_BOARD_SPECIAL_EVENT]') and entry['gacha']:
            troop = _(self.troops[entry['gacha']]['name'], lang)
            kingdom = _(self.kingdoms[entry['kingdom_id']]['name'], lang)
            entry['extra_info'] = f'{troop} ({kingdom})'

        entry['type'] = _(entry['type'], lang)
        return entry

    def get_campaign_tasks(self, lang):
        return {
            _('[MEDAL_LEVEL_0]'): [self.translate_campaign_task(t, lang) for t in self.campaign_tasks['bronze']],
            _('[MEDAL_LEVEL_1]'): [self.translate_campaign_task(t, lang) for t in self.campaign_tasks['silver']],
            _('[MEDAL_LEVEL_2]'): [self.translate_campaign_task(t, lang) for t in self.campaign_tasks['gold']],
        }

    def translate_campaign_task(self, task, lang):
        new_task = task.copy()
        kingdom = self.kingdoms[task['kingdom_id']]
        color = kingdom['primary_color'].upper()

        replacements = {
            '{WeaponType}': '[WEAPONTYPE_{c:u}]',
            '{Kingdom}': '[{d:u}_NAME]',
            '{Banner}': '[{c:u}_BANNERNAME]',
            '{Class}': '[HEROCLASS_{c:l}_NAME]',
            '{Color}': f'[GEM_{color}]',
            '{TroopType}': '[TROOPTYPE_{value1:u}]',
            '{Troop}': '[TROOPTYPE_{value1:u}]',
        }
        new_task['title'] = _(new_task['title'], lang)
        new_task['name'] = _(new_task["name"], lang)
        for before, after in replacements.items():
            translated = _(after.format(**new_task), lang)
            if '`?`' in translated:
                translated = '`?`'
            if before in new_task['title']:
                new_task['title'] = new_task['title'].replace(before, translated)
            if before in new_task['name']:
                new_task['name'] = new_task['name'].replace(before, translated)
        if '{0}' in new_task['name']:
            new_task['name'] = new_task['name'].replace('{0}', str(new_task['x']))
        elif '{2}' in new_task['name']:
            unit = _(f'[{new_task["y"].upper()}]', lang)
            replacement = f'{new_task["x"]} {unit}'
            new_task['name'] = new_task['name'].replace('{2}', replacement)
        else:
            new_task['name'] = f'{task["x"]}x ' + new_task['name']

        return new_task

    def get_spoilers(self, lang):
        spoilers = []
        now = datetime.datetime.utcnow()
        near_term_spoilers = [s for s in self.spoilers if now <= s['date'] <= now + datetime.timedelta(days=180)]
        for spoiler in near_term_spoilers:
            translated = self.translate_spoiler(spoiler, lang)
            if translated:
                spoilers.append(translated)
        return spoilers

    def translate_spoiler(self, spoiler, lang):
        entry = getattr(self, spoiler['type'] + 's').get(spoiler['id'], {}).copy()
        if not entry:
            return None
        entry['name'] = _(entry['name'], lang)
        entry['type'] = spoiler['type']
        entry['date'] = spoiler['date'].date()
        if 'rarity' in entry:
            entry['rarity_title'] = _('[RARITY]', lang)
            if entry['rarity'] in TROOP_RARITIES:
                rarity_number = TROOP_RARITIES.index(entry['rarity'])
                entry['rarity'] = _(f'[RARITY_{rarity_number}]', lang)

        kingdom_id = entry.get('kingdom_id')
        if kingdom_id:
            kingdom = self.kingdoms[kingdom_id]
            entry['kingdom'] = _(kingdom['name'], lang)
        return entry

    @staticmethod
    def translate_categories(categories, lang):
        def try_different_translated_versions_because_devs_are_stupid(cat):
            lookup = f'[{cat.upper()}S]'
            result = _(lookup, lang)
            if result == lookup:
                result = _(f'[{cat.upper()}S:]', lang)[:-1]
            return result

        translated = [try_different_translated_versions_because_devs_are_stupid(c) for c in categories]
        return dict(zip(categories, translated))
