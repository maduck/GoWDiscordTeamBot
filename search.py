import calendar
import copy
import datetime
import importlib
import json
import logging
import operator
import re
from collections import defaultdict

import translations
from configurations import CONFIG
from data_source.game_data import GameData
from game_constants import COLORS, EVENT_TYPES, GEM_TUTORIAL_IDS, RARITY_COLORS, SOULFORGE_ALWAYS_AVAILABLE, \
    SOULFORGE_REQUIREMENTS, TROOP_RARITIES, \
    UNDERWORLD_SOULFORGE_REQUIREMENTS, WEAPON_RARITIES
from models.bookmark import Bookmark
from models.toplist import Toplist
from util import batched, dig, extract_search_tag, get_next_monday_in_locale, greatest_common_divisor, translate_day

WEEK_DAY_FORMAT = '%b %d'

LOGLEVEL = logging.DEBUG

formatter = logging.Formatter('%(asctime)-15s [%(levelname)s] %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(LOGLEVEL)
log = logging.getLogger(__name__)

log.setLevel(LOGLEVEL)
log.addHandler(handler)

t = translations.Translations()
_ = t.get


def update_translations():
    global _
    try:
        importlib.reload(translations)
        _ = translations.Translations().get
    except (NameError, json.decoder.JSONDecodeError):
        log.exception('Could not update translations, stacktrace follows.')


class TeamExpander:
    my_emojis = {}

    def __init__(self):
        world = GameData()
        world.populate_world_data()
        self.troops = world.troops
        self.troop_types = world.troop_types
        self.spells = world.spells
        self.effects = world.effects
        self.positive_effects = world.positive_effects
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
        self.campaign_week = world.campaign_week
        self.campaign_name = world.campaign_name
        self.campaign_tasks = world.campaign_tasks
        self.task_skip_costs = world.campaign_skip_costs
        self.reroll_tasks = world.campaign_rerolls
        self.soulforge = world.soulforge
        self.summons = world.summons
        self.traitstones = world.traitstones
        self.levels = world.levels
        self.rooms = {}
        self.toplists = Toplist()
        self.bookmarks = Bookmark()
        self.adventure_board = world.adventure_board
        self.drop_chances = world.drop_chances
        self.event_key_drops = world.event_chest_drops
        self.event_kingdoms = world.event_kingdoms
        self.weekly_event = world.weekly_event
        self.active_gems = world.gem_events
        self.store_data = world.store_data
        self.user_data = world.user_data
        self.hoard_potions = world.hoard_potions
        self.orbs = world.orbs

    @classmethod
    def extract_code_from_message(cls, raw_code):
        return [int(n.strip()) for n in raw_code.split(',') if n and n.isdigit()]

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

        for i, element in enumerate(code):
            if troop := self.troops.get(element):
                troop = troop.copy()
                self.translate_troop(troop, lang)
                result['troops'].append(troop)
                continue

            if weapon := self.weapons.get(element):
                weapon = weapon.copy()
                self.translate_weapon(weapon, lang)
                result['troops'].append(weapon)
                has_weapon = True
                continue

            if _class := self.classes.get(element):
                result['class'] = _(_class['name'], lang)
                result['class_talents'] = _class['talents']
                has_class = True
                continue

            if banner := self.banners.get(element):
                result['banner'] = self.translate_banner(banner, lang)
                continue

            if 0 <= element <= 3:
                result['talents'].append(element)
                self.trim_talents(result)
                continue
            has_class = self.fill_up_troops_banner_and_class(i, result, has_class, lang)

        hero_present = has_weapon and has_class
        if hero_present:
            result['talents'] = self.populate_talents(result, lang)
        else:
            result['class'] = None
            result['talents'] = None

        return result

    def fill_up_troops_banner_and_class(self, i, result, has_class, lang):
        if i <= 3:
            result['troops'].append(self.troops['`?`'])
        elif i == 4:
            banner = {
                'colors': [('questionmark', 1)],
                'name': '[REQUIREMENTS_NOT_MET]',
                'filename': 'Locked',
                'id': '`?`'
            }
            result['banner'] = self.translate_banner(banner, lang)
        elif i == 12:
            result['class'] = _('[REQUIREMENTS_NOT_MET]', lang)
            result['talents'] = []
            return True
        return has_class

    @staticmethod
    def populate_talents(result, lang):
        new_talents = []
        for talent_no, talent_code in enumerate(result['talents']):
            talent = '-'
            if talent_code > 0:
                talent = _(result['class_talents'][talent_code - 1][talent_no]['name'], lang)
            new_talents.append(talent)
        return new_talents

    def trim_talents(self, result):
        if len(result['talents']) > 7:
            result['talents'] = result['talents'][-7:]

    def get_team_from_message(self, user_code, lang):
        if code := self.extract_code_from_message(user_code):
            return self.get_team_from_code(code, lang)
        else:
            return

    @staticmethod
    def search_item(search_term, lang, items, lookup_keys, translator, sort_by='name'):
        if search_term.startswith('#'):
            search_term = search_term[1:]
        if search_term.isdigit():
            if item := items.get(int(search_term)):
                result = item.copy()
                translator(result, lang)
                return [result]
            return []
        possible_matches = []
        real_search = extract_search_tag(search_term)
        if not real_search:
            return []
        for base_item in items.values():
            if base_item['name'] == '`?`' or base_item['id'] == '`?`':
                continue
            item = base_item.copy()
            translator(item, lang)
            lookups = {
                k: extract_search_tag(dig(item, k)) for k in lookup_keys
            }

            if real_search == extract_search_tag(item['name']):
                return [item]
            for key, lookup in lookups.items():
                if real_search in lookup:
                    possible_matches.append(item)
                    break

        return sorted(possible_matches, key=operator.itemgetter(sort_by))

    def search_troop(self, search_term, lang):
        lookup_keys = [
            'name',
            'kingdom',
            'type',
            'roles',
            'spell.description',
            'shiny',
        ]
        return self.search_item(search_term, lang,
                                items=self.troops,
                                lookup_keys=lookup_keys,
                                translator=self.translate_troop)

    def translate_troop(self, troop, lang):
        troop['name'] = _(troop['name'], lang, default=troop['reference_name'])
        troop['description'] = _(troop['description'], lang).replace('widerbeleben',
                                                                     'wiederbeleben')
        troop['color_code'] = "".join(troop['colors'])
        troop['immortal_title'] = _('[TROOPTYPE_IMMORTAL]', lang)
        troop['rarity_title'] = _('[RARITY]', lang)
        troop['raw_rarity'] = troop['rarity']
        rarity_number = 1
        if troop['rarity'] in TROOP_RARITIES:
            rarity_number = TROOP_RARITIES.index(troop['rarity'])
        troop['rarity'] = _(f'[RARITY_{rarity_number}]', lang)
        troop['traits_title'] = _('[TRAITS]', lang)
        troop['traits'] = self.enrich_traits(troop['traits'], lang)
        troop['immortal_traits'] = self.enrich_traits(troop['immortal_traits'], lang)
        troop['roles_title'] = _('[TROOP_ROLE]', lang)
        troop['roles'] = [_(f'[TROOP_ROLE_{role.upper()}]', lang) for role in troop['roles']]
        troop['type_title'] = _('[FILTER_TROOPTYPE]', lang)
        troop['raw_types'] = troop['types']
        types = [
            _(f'[TROOPTYPE_{_type.upper()}]', lang) for _type in troop['types']
        ]
        troop['type'] = ' / '.join(types)
        troop['kingdom_title'] = _('[KINGDOM]', lang)
        reference_name = troop['kingdom'].get('reference_name', troop['kingdom']['name'])
        troop['kingdom'] = _(troop['kingdom']['name'], lang)
        if self.is_untranslated(troop['kingdom']):
            troop['kingdom'] = reference_name
        troop['spell'] = self.translate_spell(troop['spell_id'], lang)
        troop['spell_title'] = _('[TROOPHELP_SPELL0]', lang)
        self.translate_traitstones(troop, lang)
        troop['bonuses_title'] = _('[BONUSES]', lang)
        if troop['has_shiny']:
            troop['shiny'] = _('[SHINY_LEVEL_HINT_FIND_TOKENS]', lang)
            troop['shiny_spell'] = self.translate_spell(troop['shiny_spell_id'], lang)

    @staticmethod
    def translate_traitstones(item, lang):
        item['traitstones_title'] = _('[SOULFORGE_TAB_TRAITSTONES]', lang)
        if 'traitstones' not in item:
            item['traitstones'] = []
        traitstones = [
            f'{_(rune["name"], lang)} ({rune["amount"]})'
            for rune in item['traitstones']
        ]
        item['traitstones'] = traitstones

    @staticmethod
    def enrich_traits(traits, lang, delve_id=None):
        new_traits = []
        for trait in traits:
            new_trait = trait.copy()
            new_trait['name'] = _(trait['name'], lang)
            new_trait['description'] = _(trait['description'], lang)
            if delve_id is not None:
                new_trait['description'] = _(f'[TREASURE_HOARD_POTION_DESC_{delve_id}]', lang)
            new_traits.append(new_trait)
        return new_traits

    def search_kingdom(self, search_term, lang):
        lookup_keys = ['name']
        return self.search_item(search_term, lang, items=self.kingdoms, lookup_keys=lookup_keys,
                                translator=self.translate_kingdom)

    def search_faction(self, search_term, lang):
        lookup_keys = ['name', 'translated_colors']
        items = {k: v for k, v in self.kingdoms.items() if v['underworld']}
        return self.search_item(search_term, lang, items=items, lookup_keys=lookup_keys,
                                translator=self.translate_kingdom)

    def kingdom_summary(self, lang):
        kingdoms = [k.copy() for k in self.kingdoms.values() if k['location'] == 'krystara' and len(k['colors']) > 0]
        for kingdom in kingdoms:
            self.translate_kingdom(kingdom, lang)
        return sorted(kingdoms, key=operator.itemgetter('name'))

    def translate_kingdom(self, kingdom, lang):
        kingdom['name'] = _(kingdom['name'], lang)
        if self.is_untranslated(kingdom['name']):
            kingdom['name'] = kingdom['reference_name']
        kingdom['description'] = _(kingdom['description'], lang)
        kingdom['punchline'] = _(kingdom['punchline'], lang)
        kingdom['troop_title'] = _('[TROOPS]', lang)

        kingdom['troops'] = []
        for troop_id in kingdom['troop_ids']:
            if troop_id not in self.troops:
                continue
            troop = self.troops[troop_id].copy()
            self.translate_troop(troop, lang)
            kingdom['troops'].append(troop)

        kingdom['troops'] = sorted(kingdom['troops'], key=operator.itemgetter('name'))
        kingdom['weapons_title'] = _('[WEAPONS:]', lang)
        kingdom['weapons'] = sorted([
            {'name': _(self.weapons[_id]['name'], lang),
             'id': _id
             } for _id in kingdom['weapon_ids']
        ], key=operator.itemgetter('name'))
        kingdom['banner_title'] = _('[BANNERS]', lang)
        kingdom['banner'] = self.translate_banner(self.banners[kingdom['id']], lang)

        kingdom['linked_kingdom'] = None
        if kingdom['linked_kingdom_id']:
            kingdom['linked_kingdom'] = _(self.kingdoms[kingdom['linked_kingdom_id']]['name'], lang)
        if kingdom['linked_kingdom'] and self.is_untranslated(kingdom['linked_kingdom']):
            kingdom['linked_kingdom'] = None
        kingdom['map'] = _('[MAPNAME_MAIN]', lang)
        kingdom['linked_map'] = _('[MAPNAME_UNDERWORLD]', lang)
        if kingdom['underworld']:
            kingdom['map'] = _('[MAPNAME_UNDERWORLD]', lang)
            kingdom['linked_map'] = _('[MAPNAME_MAIN]', lang)
        if 'primary_color' in kingdom:
            deed_num = COLORS.index(kingdom['primary_color'])
            kingdom['deed'] = _(f'[DEED{deed_num:02d}]', lang)
        color_emojis = [self.my_emojis.get(c) for c in kingdom['colors']]
        kingdom['color_emojis'] = "".join(color_emojis)
        kingdom['translated_colors'] = [_(f'[GEM_{c.upper()}]', lang) for c in kingdom['colors']]
        kingdom['color_title'] = _('[GEM_MASTERY]', lang)
        kingdom['stat_title'] = _('[STAT_BONUS]', lang)
        if 'class_id' in kingdom:
            kingdom['class_title'] = _('[CLASS]', lang)
            kingdom['class'] = _(self.classes[kingdom['class_id']]['name'], lang)
        if 'primary_stat' in kingdom:
            kingdom['primary_stat'] = _(f'[{kingdom["primary_stat"].upper()}]', lang)
        if 'pet' in kingdom:
            kingdom['pet_title'] = _('[PET_RESCUE_PET]', lang)
            kingdom['pet'] = kingdom['pet'].translations[lang]
        if 'event_weapon' in kingdom:
            kingdom['event_weapon_title'] = _('[FACTION_WEAPON]', lang)
            kingdom['event_weapon_id'] = kingdom['event_weapon']['id']
            event_weapon = kingdom['event_weapon'].copy()
            self.translate_weapon(event_weapon, lang)
            kingdom['event_weapon'] = event_weapon
        kingdom['max_power_level_title'] = _('[KINGDOM_POWER_LEVELS]', lang)

    def search_class(self, search_term, lang):
        lookup_keys = ['name']
        return self.search_item(search_term, lang,
                                items=self.classes,
                                translator=self.translate_class,
                                lookup_keys=lookup_keys)

    def class_summary(self, lang):
        classes = [c.copy() for c in self.classes.values()]
        for c in classes:
            self.translate_class(c, lang)
        return sorted(classes, key=operator.itemgetter('name'))

    def translate_class(self, _class, lang):
        kingdom = self.kingdoms[_class['kingdom_id']]
        _class['kingdom'] = _(kingdom['name'], lang, default=kingdom['reference_name'])
        weapon = self.weapons[_class['weapon_id']]
        _class['weapon'] = _(weapon['name'], lang)
        _class['name'] = _(_class['name'], lang)
        translated_trees = []
        for tree in _class['talents']:
            translated_talents = [
                {
                    'name': _(talent['name'], lang),
                    'description': _(talent['description'], lang),
                }
                for talent in tree
            ]
            translated_trees.append(translated_talents)
        self.translate_traitstones(_class, lang)
        _class['talents_title'] = _('[TALENT_TREES]', lang)
        _class['kingdom_title'] = _('[KINGDOM]', lang)
        _class['traits_title'] = _('[TRAITS]', lang)
        _class['traits'] = self.enrich_traits(_class['traits'], lang)
        _class['weapon_title'] = _('[WEAPON]', lang)
        _class['talents'] = translated_trees
        _class['trees'] = [_(f'[TALENT_TREE_{tree.upper()}]', lang) for tree in _class['trees']]
        _class['type_short'] = _(f'[TROOPTYPE_{_class["type"].upper()}]', lang)
        _class['type'] = _(f'[PERK_TYPE_{_class["type"].upper()}]', lang)
        _class['weapon_bonus'] = _('[MAGIC_BONUS]', lang) + " " + _(
            f'[MAGIC_BONUS_{COLORS.index(_class["weapon_color"])}]', lang)

    def get_all_talents(self, lang):
        result = []
        for input_tree in self.talent_trees.values():
            tree = input_tree.copy()
            self.translate_talent_tree(tree, lang)
            result.append(tree)
        return sorted(result, key=operator.itemgetter('name'))

    def search_talent(self, search_term, lang):
        possible_matches = []
        for tree in self.talent_trees.values():
            translated_name = extract_search_tag(_(tree['name'], lang))
            translated_talents = [_(talent['name'], lang) for talent in tree['talents']]
            talents_search_tags = [extract_search_tag(talent) for talent in translated_talents]
            real_search = extract_search_tag(search_term)
            if real_search == translated_name or real_search in talents_search_tags:
                result = tree.copy()
                self.translate_talent_tree(result, lang)
                return [result]
            elif real_search in translated_name:
                result = tree.copy()
                self.translate_talent_tree(result, lang)
                possible_matches.append(result)
            elif talent_matches := [
                tag for tag in talents_search_tags if real_search in tag
            ]:
                result = tree.copy()
                result['talent_matches'] = talent_matches
                self.translate_talent_tree(result, lang)
                possible_matches.append(result)
        return sorted(possible_matches, key=operator.itemgetter('name'))

    @staticmethod
    def translate_talent_tree(tree, lang):
        tree['talents_title'] = _('[TALENT_TREES]', lang)
        tree['name'] = _(tree['name'], lang)
        translated_talents = [
            {
                'name': _(talent['name'], lang),
                'description': _(talent['description'], lang),
            }
            for talent in tree['talents']
        ]
        tree['talents'] = translated_talents
        tree['classes'] = [
            {'id': c['id'],
             'name': _(c['name'], lang)
             }
            for c in tree['classes']
        ]

    def get_troops_with_trait(self, trait, lang):
        return self.get_objects_by_trait(trait, self.troops, self.translate_troop, lang)

    def get_classes_with_trait(self, trait, lang):
        return self.get_objects_by_trait(trait, self.classes, self.translate_class, lang)

    @staticmethod
    def get_objects_by_trait(trait, objects, translator, lang):
        result = []
        for o in objects.values():
            trait_codes = [trait['code'] for trait in o['traits']] if 'traits' in o else []
            if trait['code'] in trait_codes:
                translated_object = o.copy()
                translator(translated_object, lang)
                result.append(translated_object)
        return result

    def search_trait(self, search_term, lang):
        possible_matches = []
        for code, trait in self.traits.items():
            translated_name = extract_search_tag(_(trait['name'], lang))
            translated_description = extract_search_tag(_(trait['description'], lang))
            real_search = extract_search_tag(search_term)
            if real_search == translated_name:
                result = trait.copy()
                result['troops'] = self.get_troops_with_trait(trait, lang)
                result['troops_title'] = _('[TROOPS]', lang)
                result['classes'] = self.get_classes_with_trait(trait, lang)
                result['classes_title'] = _('[CLASS]', lang)
                if result['troops'] or result['classes']:
                    return self.enrich_traits([result], lang)
            elif real_search in translated_name or real_search in translated_description:
                result = trait.copy()
                result['troops'] = self.get_troops_with_trait(trait, lang)
                result['troops_title'] = _('[TROOPS]', lang)
                result['classes'] = self.get_classes_with_trait(trait, lang)
                result['classes_title'] = _('[CLASS]', lang)
                if result['troops'] or result['classes']:
                    possible_matches.append(result)
        return sorted(self.enrich_traits(possible_matches, lang), key=operator.itemgetter('name'))

    def search_pet(self, search_term, lang):
        return self.pets.search(search_term, lang)

    def search_weapon(self, search_term, lang):
        lookup_keys = [
            'name',
            'type',
            'roles',
            'spell.description',
        ]
        return self.search_item(search_term, lang,
                                items=self.weapons,
                                lookup_keys=lookup_keys,
                                translator=self.translate_weapon)

    def translate_weapon(self, weapon, lang):
        weapon['name'] = _(weapon['name'], lang)
        weapon['description'] = _(weapon['description'], lang)
        weapon['color_code'] = "".join(sorted(weapon['colors']))
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
            upgrades.extend(
                {
                    'name': f'{upgrade_titles[i]} {bonus_title}',
                    'description': f'+{amount} {upgrade_titles[i]}',
                }
                for i, amount in enumerate(upgrade)
                if amount
            )
        weapon['upgrades'] = upgrades + [self.translate_spell(spell['id'], lang) for spell in weapon['affixes']]
        weapon['kingdom_title'] = _('[KINGDOM]', lang)
        weapon['kingdom_id'] = weapon['kingdom']['id']
        weapon['kingdom'] = _(weapon['kingdom']['name'], lang, default=weapon['kingdom']['reference_name'])
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
            _class = _(weapon.get('class', '[NO_CLASS]'), lang)
            weapon['requirement_text'] = _('[CLASS_REWARD_TITLE]', lang) + f' ({_class})'
        elif weapon['requirement'] == 1003:
            weapon['requirement_text'] = _('[SOULFORGE_WEAPONS_TAB_EMPTY_ERROR]', lang)
        if weapon.get('event_faction'):
            weapon['requirement_text'] += ' (' + _(f'[{weapon["event_faction"]}_NAME]', lang) + ' ' + _(
                '[FACTION_WEAPON]', lang) + ')'

    def search_affix(self, search_term, lang):
        real_search = extract_search_tag(search_term)
        results = {}
        for weapon in self.weapons.values():
            my_weapon = weapon.copy()
            self.translate_weapon(my_weapon, lang)
            affixes = [affix for affix in my_weapon['upgrades'] if 'cost' in affix]
            for affix in affixes:
                search_name = extract_search_tag(affix['name'])
                search_desc = extract_search_tag(affix['description'])
                if real_search == search_name \
                        or real_search == search_desc \
                        or real_search in search_name \
                        or real_search in search_desc:
                    if affix['name'] in results:
                        results[affix['name']]['weapons'].append(my_weapon)
                        results[affix['name']]['num_weapons'] += 1
                    else:
                        results[affix['name']] = affix.copy()
                        results[affix['name']]['weapons_title'] = _('[SOULFORGE_TAB_WEAPONS]', lang)
                        results[affix['name']]['weapons'] = [my_weapon]
                        results[affix['name']]['num_weapons'] = 1
        for name, affix in results.items():
            if real_search == extract_search_tag(name):
                return [affix]
        return sorted(results.values(), key=operator.itemgetter('name'))

    def search_traitstone(self, search_term, lang):
        return self.search_item(search_term, lang,
                                items=self.traitstones,
                                lookup_keys=['name'],
                                translator=self.translate_traitstone)

    def translate_traitstone(self, traitstone, lang):
        troops = []
        for troop_id in traitstone['troop_ids']:
            amount = sum(troop['amount']
                         for troop in self.troops[troop_id]['traitstones']
                         if troop['id'] == traitstone['id'])
            troops.append([_(self.troops[troop_id]['name'], lang), amount])
        traitstone['troops'] = sorted(troops, key=operator.itemgetter(1), reverse=True)

        classes = []
        for class_id in traitstone['class_ids']:
            amount = sum(_class['amount'] for _class in self.classes[class_id]['traitstones']
                         if _class['id'] == traitstone['id'])
            classes.append([_(self.classes[class_id]['name'], lang), amount])
        traitstone['classes'] = classes

        kingdoms = [
            _(self.kingdoms[int(kingdom_id)]['name'], lang)
            for kingdom_id in traitstone['kingdom_ids']
        ]
        if not traitstone['kingdom_ids']:
            kingdoms.append(_('[ALL_KINGDOMS]', lang))
        traitstone['kingdoms'] = kingdoms

        traitstone['name'] = _(traitstone['name'], lang)
        traitstone['troops_title'] = _('[TROOPS]', lang)
        traitstone['classes_title'] = _('[CLASS]', lang)
        traitstone['kingdoms_title'] = _('[KINGDOMS]', lang)

    def translate_spell(self, spell_id, lang):
        spell = self.spells[spell_id]
        magic = _('[MAGIC]', lang)

        description = self.translate_spell_description(spell['description'], lang)

        for i, (multiplier, amount) in enumerate(spell['effects'], start=1):
            spell_amount = f' + {amount}' if amount else ''
            divisor, multiplier_text = self.translate_spell_multiplier(multiplier)
            damage = f'[{multiplier_text}{magic}{divisor}{spell_amount}]'
            number_of_replacements = len(re.findall(r'\{\d}', description))
            has_half_replacement = len(spell['effects']) == number_of_replacements - 1
            if '{2}' in description and has_half_replacement:
                multiplier *= 0.5
                amount *= 0.5
                if amount == int(amount):
                    amount = int(amount)
                half_damage = f'[{multiplier} ⨯ {magic}{divisor} + {amount}]'
                description = description.replace('{1}', half_damage)
                description = description.replace('{2}', damage)
            else:
                description = description.replace(f'{{{i}}}', damage)

        if boost := self.calculate_boost_ratio(spell):
            boost = f" [{_('[BOOST_RATIO]', lang)} {boost}]"

        description = f'{description}{boost}'

        return {
            'name': _(spell['name'], lang),
            'cost': spell['cost'],
            'description': description,
        }

    def translate_spell_multiplier(self, multiplier):
        multiplier_text = ''
        if multiplier > 1:
            if multiplier == int(multiplier):
                multiplier_text = f'{multiplier:.0f} ⨯ '
            else:
                multiplier_text = f'{multiplier} ⨯ '
        divisor = ''
        if multiplier < 1:
            number = round(1 / multiplier, 2)
            divisor = f' / {number}'
        return divisor, multiplier_text

    @staticmethod
    def calculate_boost_ratio(spell):
        if not spell['boost']:
            return ''
        if spell['boost'] <= 100:
            return f'{round(100 / spell["boost"])}:1'
        if spell['boost'] > 100:
            return f'x{round(spell["boost"] / 100)}'
        gcd = greatest_common_divisor(spell['boost'], 100)
        return f'{spell["boost"] // gcd}:{100 // gcd}'

    def translate_spell_description(self, description, lang):
        description = _(description, lang)
        if description.startswith('&&'):
            description = description \
                .replace('&&', _('[CHOICE_CHOOSE_ONE_DESC]', lang), 1) \
                .replace('&&', _('[OR_CAPITALISED]', lang))
        return description

    def translate_banner(self, banner, lang):
        result = {
            'name': _(banner['name'], lang),
            'kingdom': _(self.kingdoms[banner['id']]['name'], lang),
            'colors': [(_(c[0], 'en').lower(), c[1]) for c in banner['colors'] if c[1]],
            'filename': banner['filename'],
        }
        colors_shorthand = []
        for color, amount in result['colors']:
            if amount > 0:
                colors_shorthand.append(color[0].upper())
            else:
                colors_shorthand.append(color[0].lower())
        result['colors_shorthand'] = ''.join(colors_shorthand)
        if not result['colors']:
            result['available'] = _('[AVAILABLE_FROM_KINGDOM]', lang).replace('%1', _(f'[{banner["id"]}_NAME]', lang))
        return result

    def get_event_kingdoms(self, lang):
        today = datetime.date.today()
        start = today + datetime.timedelta(days=-today.weekday(), weeks=1)
        result = self.guess_weekly_kingdom_from_troop_spoilers(lang)

        prediction = ''
        for kingdom_id in self.event_kingdoms:
            end = start + datetime.timedelta(days=7)
            if kingdom_id != 0:
                event_data = {
                    'start': start,
                    'end': end,
                    'kingdom': _(self.kingdoms[kingdom_id]['name'], lang,
                                 default=self.kingdoms[kingdom_id]['reference_name']) + prediction,
                }
                result[start] = event_data
            else:
                prediction = ' *'
            start = end
        return sorted(result.values(), key=operator.itemgetter('start'))

    def guess_weekly_kingdom_from_troop_spoilers(self, lang):
        result = {}
        latest_date = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        for spoiler in self.spoilers:
            if spoiler['type'] == 'troop' \
                    and spoiler['date'].weekday() == 0 \
                    and spoiler['date'] > latest_date:
                troop = self.troops[spoiler['id']]
                if troop['rarity'] == 'Mythic':
                    continue
                kingdom = troop['kingdom']
                if not kingdom.get('name') and not kingdom.get('reference_name'):
                    continue
                if kingdom['id'] in self.event_kingdoms:
                    continue
                result[spoiler['date'].date()] = {
                    'start': spoiler['date'].date(),
                    'end': spoiler['date'].date() + datetime.timedelta(days=7),
                    'kingdom': _(kingdom['name'], lang,
                                 default=kingdom['reference_name']) + ' *',
                }
                latest_date = spoiler['date']
        return result

    def get_events(self, lang):
        today = datetime.date.today()
        return [
            self.translate_event(e, lang)
            for e in self.events
            if today <= e['start']
        ]

    def _extend_event_extra_info(self, entry, lang):
        event_type = entry['type']
        gacha = entry['gacha']
        gacha_pools = {
            '[BOUNTY]': self.troops,
            '[HIJACK]': self.troops,
            '[DELVE_EVENT]': self.troops,
            '[RAIDBOSS]': self.troops,
            '[TOWER_OF_DOOM]': self.troops,
            '[CLASS_EVENT]': self.classes,
        }
        gacha_pool = gacha_pools.get(event_type)
        if gacha_pool and gacha and gacha in gacha_pool:
            item = gacha_pool[gacha]
            return _(item['name'], lang, default=item.get('reference_name', item['name']))
        elif event_type == '[PETRESCUE]' and gacha and gacha in self.pets:
            return self.pets[gacha][lang].name
        elif event_type == '[HIJACK]' and entry['troops']:
            troops = [self.troops[troop] for troop in entry['troops']]
            return ', '.join(_(troop['name'], lang, default=troop['reference_name']) for troop in troops)
        return ''

    def translate_event(self, event, lang):
        entry = event.copy()

        entry['extra_info'] = self._extend_event_extra_info(entry, lang)
        if entry['type'] == '[INVASION]' and entry['gacha'] and entry['gacha'] in self.troops:
            troop = self.troops[entry['gacha']]
            troop_name = _(troop['name'], lang)
            entry['kingdom_id'] = troop.get('kingdom_id', '`?`')
            troop_types = [_(f'[TROOPTYPE_{tt.upper()}]', lang) for tt in troop['types']]
            entry['extra_info'] = f'{troop_name} ({", ".join(troop_types)})'
        elif entry['type'] in ('[WEEKLY_EVENT]', '[RARITY_5]') and entry['gacha'] and entry['gacha'] in self.troops:
            troop = self.troops[entry['gacha']]
            troop_name = _(troop['name'], lang, default=troop['reference_name'])
            kingdom = _(self.kingdoms[entry['kingdom_id']]['name'], lang,
                        default=self.kingdoms[entry['kingdom_id']]['reference_name'])
            entry['extra_info'] = f'{troop_name} ({kingdom})'
            entry['kingdom'] = kingdom
        elif entry['type'] == '[VAULT]':
            entry['kingdom_id'] = 3038

        if entry['kingdom_id']:
            kingdom = self.kingdoms[entry['kingdom_id']]
            entry['kingdom'] = _(kingdom['name'], lang, default=kingdom['reference_name'])

        locale = translations.LANGUAGE_CODE_MAPPING.get(lang, lang)
        locale = translations.LOCALE_MAPPING.get(locale, 'en_GB') + '.UTF8'
        with calendar.different_locale(locale):
            entry['formatted_start'] = entry['start'].strftime(WEEK_DAY_FORMAT)
            entry['start_day'] = entry['start'].strftime('%A')
            entry['formatted_end'] = entry['end'].strftime(WEEK_DAY_FORMAT)
            entry['end_day'] = entry['end'].strftime('%A')

        entry['raw_type'] = entry['type']
        entry['type'] = _(entry['type'], lang)
        if self.is_untranslated(entry['type']) and entry['names']:
            entry['type'] = entry['names'][translations.LOCALE_MAPPING[lang].replace('en_GB', 'en_US')]

        return entry

    def get_campaign_tasks(self, lang, _filter=None):
        result = {'heading': f'{_("[CAMPAIGN]", lang)}: {_("[TASKS]", lang)}'}
        tiers = ['bronze', 'silver', 'gold']
        result['campaigns'] = {
            f'[MEDAL_LEVEL_{i}]': [self.translate_campaign_task(task, lang) for task in self.campaign_tasks[tier]]
            for i, tier in reversed(list(enumerate(tiers))) if _filter is None or tier.lower() == _filter.lower()
        }
        formatted_start, start_date = get_next_monday_in_locale(date=None, lang=lang)
        result['has_content'] = any(len(c) > 0 for c in result['campaigns'].values())
        result['background'] = f'Background/{self.campaign_tasks["kingdom"]["filename"]}_full.png'
        result['gow_logo'] = 'Atlas/gow_logo.png'
        kingdom_filebase = self.campaign_tasks['kingdom']['filename']
        result['kingdom_logo'] = f'Troopcardshields_{kingdom_filebase}_full.png'
        result['kingdom'] = _(self.campaign_tasks['kingdom']['name'], lang)
        result['raw_date'] = start_date
        result['date'] = formatted_start
        result['lang'] = lang
        result['texts'] = {
            'campaign': _('[CAMPAIGN]', lang),
            'team': _('[LITE_CHAT_TEAM_START]', lang),
        }
        return result

    def get_reroll_tasks(self, lang, _filter=None):
        tiers = ['bronze', 'silver', 'gold']
        return {
            f'[MEDAL_LEVEL_{i}]': [
                self.translate_campaign_task(task, lang)
                for task in self.reroll_tasks[tier]
            ]
            for i, tier in reversed(list(enumerate(tiers)))
            if _filter is None or tier.lower() == _filter.lower()
        }

    def __task_name_replacements(self, task, color, lang):
        replacements = {
            '{WeaponType}': '[WEAPONTYPE_{c:u}]',
            '{Kingdom}': '[{d:u}_NAME]',
            '{Banner}': '[{c:u}_BANNERNAME]',
            '{Class}': '[HEROCLASS_{c:l}_NAME]',
            '{Color}': f'[GEM_{color}]',
            '{TroopType}': '[TROOPTYPE_{value1:u}]',
            '{Troop}': '{{[{value1}][name]}}',
            '{Value0}': task['value0'],
            '{Value1}': task['value1'],
            '{0}': '{x}',
            '{1}': task['c'],
            '{2}': '{x} {y}',
        }
        for before, after in replacements.items():
            if before in task['title'] or before in task['name']:
                translated = _(after.format(**task).format(self.troops), lang, plural=task['plural'])
                if '`?`' in translated:
                    translated = '`?`'
                task['title'] = task['title'].replace(before, translated)
                task['name'] = task['name'].replace(before, translated)

    def translate_campaign_task(self, task, lang):
        new_task = task.copy()
        color_code = int(new_task['value1']) if new_task['value1'].isdigit() else 666
        color = COLORS[color_code].upper() if color_code < len(COLORS) else '`?`'
        if isinstance(new_task.get('y'), str):
            new_task['y'] = _(f'[{new_task["y"].upper()}]', lang)
        new_task['plural'] = int(new_task.get('x', 1)) != 1
        new_task['title'] = _(new_task['title'], lang, plural=new_task['plural'])
        new_task['name'] = _(new_task["name"], lang, plural=new_task['plural'])
        if '{0}' not in new_task['name'] and '{2}' not in new_task['name']:
            new_task['name'] = f'{task["x"]}x ' + new_task['name']

        self.__task_name_replacements(new_task, color, lang)
        new_task['name'] += self.__task_solution_location(new_task, task, color, lang)

        return new_task

    def __task_solution_location(self, new_task, task, color, lang):
        where = ''
        if new_task['value1'] == '`?`':
            pass
        elif task['name'] == '[TASK_KILL_TROOP_COLOR]' and color != '`?`':
            color_kingdoms = self.get_color_kingdoms(lang)
            target_kingdom = color_kingdoms[color.lower()]['name']
            where = f' --> {target_kingdom}'
        elif task['name'] == '[TASK_KILL_TROOP_ID]':
            target_kingdom = _(self.troops[int(task['value1'])]['kingdom']['name'], lang)
            pvp = _('[PVP]', lang)
            weekly_event = _('[WEEKLY_EVENT]', lang)
            where = f' --> {target_kingdom} / {pvp} / {weekly_event}'
        elif task['name'] == '[TASK_KILL_TROOP_TYPE]':
            troop_type_kingdoms = dict(self.get_type_kingdoms(lang))
            troop_type = _(f'[TROOPTYPE_{task["value1"].upper()}]', lang)
            target_kingdom = troop_type_kingdoms[troop_type]['name']
            where = f' --> {target_kingdom}'
        elif task['name'] == '[TASK_KILL_TREASURE_GNOMES]':
            vault = _(self.kingdoms[3038]['name'], lang)
            where = f' --> {vault}'
        return where

    def get_spoilers(self, lang):
        spoilers = []
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        near_term_spoilers = [s for s in self.spoilers if now <= s['date'] <= now + datetime.timedelta(days=180)]
        for spoiler in near_term_spoilers:
            if translated := self.translate_spoiler(spoiler, lang):
                spoilers.append(translated)
        return spoilers

    def translate_spoiler(self, spoiler, lang):
        # this is transitional until all new models are in place.
        if spoiler['type'] in ['pet']:
            if item := getattr(self, spoiler['type'] + 's').get(spoiler['id']):
                entry = item[translations.LANGUAGE_CODE_MAPPING.get(lang, lang)].data.copy()
            else:
                return
        else:
            entry = getattr(self, spoiler['type'] + 's').get(spoiler['id'], {}).copy()
        if not entry:
            return None
        entry['name'] = _(entry['name'], lang)
        if self.is_untranslated(entry['name']):
            entry['name'] = entry.get('reference_name', entry['name'])
        entry['type'] = spoiler['type']
        entry['date'] = spoiler['date'].date()
        entry['event'] = _('[GLOG_EVENT]', lang) + ': ' if entry.get('event') else ''
        if 'rarity' in entry:
            entry['rarity_title'] = _('[RARITY]', lang)
            if entry['rarity'] in TROOP_RARITIES:
                rarity_number = TROOP_RARITIES.index(entry['rarity'])
                entry['rarity'] = _(f'[RARITY_{rarity_number}]', lang)

        if kingdom_id := entry.get('kingdom_id'):
            kingdom = self.kingdoms[kingdom_id]
            entry['kingdom'] = _(kingdom['name'], lang)
            if self.is_untranslated(entry['kingdom']):
                entry['kingdom'] = kingdom['reference_name']
        return entry

    def get_soulforge(self, lang):
        title = _('[SOULFORGE]', lang)
        craftable_items = {}
        for category, recipes in self.soulforge.items():
            recipe_type = _(category, lang)
            craftable_items[recipe_type] = [self.translate_recipe(r, lang) for r in recipes]
        return title, craftable_items

    def get_summons(self, lang):
        title = _('[SUMMONING_STONE_MENU_HEADING]', lang)
        result = {}
        for stone, contents in self.summons.items():
            stone_name = _(stone, lang)
            troops = [
                {
                    'name': _(self.troops[troop['troop_id']]['name'], lang),
                    'rarity': self.troops[troop['troop_id']]['rarity'],
                    'count': troop['count'],
                    'id': troop['troop_id']
                }
                for troop in contents
            ]
            result[stone_name] = troops
        return title, result

    @staticmethod
    def translate_recipe(recipe, lang):
        new_recipe = recipe.copy()
        new_recipe['name'] = _(recipe['name'], lang)
        rarity_number = WEAPON_RARITIES.index(new_recipe['rarity'])
        new_recipe['rarity_number'] = rarity_number
        new_recipe['raw_rarity'] = new_recipe['rarity']
        new_recipe['rarity'] = _(f'[RARITY_{rarity_number}]', lang)
        return new_recipe

    @staticmethod
    def translate_categories(categories, lang):
        def try_different_translated_versions_because_devs_are_stupid(cat):
            lookup = f'[{cat.upper()}S]'
            result = _(lookup, lang)
            if result == lookup:
                lookup = f'[{cat.upper()}S:]'
                result = _(lookup, lang)[:-1]
            if result == lookup[:-1]:
                result = _(f'[{cat.upper()}]', lang)
            if result == '[CLASSE]':
                result = _('[CLASS]', lang)
            return result

        translated = [try_different_translated_versions_because_devs_are_stupid(c) for c in categories]
        return dict(zip(categories, translated))

    def get_levels(self, lang):
        return [
            {
                'level': level['level'],
                'bonus': _(level['bonus'], lang),
            }
            for level in self.levels
        ]

    def translate_toplist(self, toplist_id, lang):
        toplist = self.toplists.get(toplist_id)
        if not toplist:
            return None
        result = toplist.copy()
        result['items'] = []
        for item_search in toplist['items']:
            items = self.search_troop(item_search, lang)
            if not items:
                items = self.search_weapon(item_search, lang)
            if not items:
                continue
            result['items'].append(items[0])
        return result

    async def create_toplist(self, message, description, items, lang, update_id):
        toplist_id = await self.toplists.add(message.author.id, message.author.display_name, description, items,
                                             update_id)
        return self.translate_toplist(toplist_id, lang)

    def kingdom_percentage(self, filter_name, filter_values, lang):
        result = {}
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        hidden_kingdoms = [3032, 3033, 3034, 3038]

        for filter_ in filter_values:
            kingdoms = []
            for kingdom in self.kingdoms.values():
                if kingdom['location'] != 'krystara':
                    continue
                if kingdom['id'] in hidden_kingdoms:
                    continue
                all_troops = [self.troops.get(troop_id) for troop_id in kingdom['troop_ids']]
                explore_troops = [
                    troop for troop in all_troops
                    if troop
                       and troop.get('release_date', now) <= now
                       and troop.get('rarity') not in [None, 'Legendary', 'Mythic']
                ]
                if not explore_troops:
                    continue
                fitting_troops = [troop for troop in explore_troops if filter_ in troop[filter_name]]
                kingdoms.append({
                    'name': _(kingdom['name'], lang),
                    'total': len(explore_troops),
                    'fitting_troops': len(fitting_troops),
                    'percentage': len(fitting_troops) / len(explore_troops),
                })
            top_kingdom = sorted(kingdoms, key=operator.itemgetter('percentage'), reverse=True)[0]
            result[filter_] = top_kingdom
        return result

    def get_color_kingdoms(self, lang):
        colors_without_skulls = COLORS[:6]
        return self.kingdom_percentage('colors', colors_without_skulls, lang)

    def get_type_kingdoms(self, lang):
        forbidden_types = {'None', 'Boss', 'Tower', 'Castle', 'Doom', 'Gnome'}
        troop_types = self.troop_types - forbidden_types
        result = self.kingdom_percentage('types', troop_types, lang)
        translated_result = {
            _(f"[TROOPTYPE_{troop_type.upper()}]", lang): kingdom
            for troop_type, kingdom in result.items()
        }
        return sorted(translated_result.items(), key=operator.itemgetter(0))

    def get_adventure_board(self, lang):
        return [
            self.translate_adventure(adventure, lang)
            for adventure in self.adventure_board
        ]

    @staticmethod
    def translate_adventure(adventure, lang):
        def change_form(key, value):
            if value == 1 and key.startswith('[KEYTYPE'):
                key = key.replace('_TITLE', '_SINGLE')
            return _(key, lang).replace('%1 ', ''), value

        result = adventure.copy()
        result['name'] = _(result['name'], lang)
        result['reward_types'] = set(result['rewards'].keys())
        result['rewards'] = dict([change_form(key, value) for key, value in result['rewards'].items()])
        result['rarity'] = _(result['rarity'], lang)
        return result

    @staticmethod
    def is_untranslated(param):
        return param[0] + param[-1] == '[]' if param else True

    def get_toplist_troop_ids(self, items, lang):
        result = []
        for search_term in items.split(','):
            items = self.search_troop(search_term, lang)
            if not items:
                items = self.search_weapon(search_term, lang)
            if items:
                result.append(str(items[0]['id']))
        return result

    def get_soulforge_weapon_image_data(self, search_term, date, switch, lang):
        search_result = self.search_weapon(search_term, lang)
        if len(search_result) != 1:
            return
        weapon = search_result[0].copy()

        requirements = SOULFORGE_REQUIREMENTS[weapon['raw_rarity']].copy()
        alternate_kingdom_id = weapon.get('event_faction')
        if alternate_kingdom_id:
            requirements = UNDERWORLD_SOULFORGE_REQUIREMENTS[weapon['raw_rarity']].copy()

        jewels = []
        for color in weapon['colors']:
            color_code = COLORS.index(color)
            filename = f'Runes_Jewel{color_code:02n}_full.png'
            jewels.append({
                'filename': filename,
                'amount': requirements['jewels'],
                'available_on': translate_day(color_code, lang),
                'kingdoms': sorted([_(kingdom['name'], lang) for kingdom in self.kingdoms.values()
                                    if 'primary_color' in kingdom
                                    and color == kingdom['primary_color']
                                    and kingdom['location'] == 'krystara']),
            })
        requirements['jewels'] = jewels
        kingdom = self.kingdoms[weapon['kingdom_id']]
        alternate_kingdom_name = None
        alternate_kingdom_filename = None
        if alternate_kingdom_id:
            alternate_kingdom = self.kingdoms[alternate_kingdom_id]
            alternate_kingdom_name = _(alternate_kingdom['name'], lang)
            alternate_kingdom_filename = alternate_kingdom['filename']

        affixes = [{
            'name': _(affix['name'], lang),
            'description': _(affix['description'], lang),
            'color': list(RARITY_COLORS.values())[i],
        } for i, affix in enumerate(weapon['affixes'], start=1)]
        mana_colors = ''.join([c.title() for c in weapon['colors']]).replace('Brown', 'Orange')
        kingdom_filebase = self.kingdoms[weapon['kingdom_id']]['filename']
        in_soulforge_text = _('[WEAPON_AVAILABLE_FROM_SOULFORGE]', lang)
        if alternate_kingdom_id:
            in_soulforge_text += ' (' + _(f'[{weapon["event_faction"]}_NAME]', lang) + ' ' + _(
                '[FACTION_WEAPON]', lang) + ')'
        date = get_next_monday_in_locale(date, lang)[0]
        return {
            'switch': switch,
            'name': weapon['name'],
            'rarity_color': RARITY_COLORS[weapon['raw_rarity']],
            'rarity': weapon['rarity'],
            'filename': f'Spells/Cards_{weapon["spell_id"]}_full.png',
            'description': weapon['spell']['description'],
            'kingdom': weapon['kingdom'],
            'alternate_kingdom': alternate_kingdom_name,
            'kingdom_logo': f'Troopcardshields_{kingdom_filebase}_full.png',
            'alternate_kingdom_logo': f'Troopcardshields_{alternate_kingdom_filename}_full.png',
            'type': _(weapon['type'], lang),
            'background': f'Background/{kingdom["filename"]}_full.png',
            'gow_logo': 'Atlas/gow_logo.png',
            'requirements': requirements,
            'affixes': affixes,
            'affix_icon': 'Atlas/affix.png',
            'gold_medal': 'Atlas/medal_gold.png',
            'mana_color': f'Troopcardall_{mana_colors}_full.png',
            'mana_cost': weapon['spell']['cost'],
            'stat_increases': {
                'attack': sum(weapon['attack_increase']),
                'health': sum(weapon['health_increase']),
                'armor': sum(weapon['armor_increase']),
                'magic': sum(weapon['magic_increase']),
            },
            'stat_icon': 'Atlas/{stat}.png',
            'texts': {
                'from_battles': _('[PET_LOOT_BONUS]', lang)
                .replace('+%1% %2 ', '')
                .replace('+%1 %2 ', ''),
                'gem_bounty': _('[DUNGEON_OFFER_NAME]', lang),
                'kingdom_challenges': f'{_("[KINGDOM]", lang)} {_("[CHALLENGES]", lang)}',
                'soulforge': _('[SOULFORGE]', lang),
                'resources': _('[RESOURCES]', lang),
                'dungeon': _('[DUNGEON]', lang),
                'dungeon_battles': _('[TASK_WIN_DUNGEON_BATTLES]', lang)
                .replace('{0}', '3')
                .replace('\x19', 's'),
                'tier_8': _('[CHALLENGE_TIER_8_ROMAN]', lang),
                'available': _('[AVAILABLE]', lang),
                'in_soulforge': in_soulforge_text,
                'n_gems': _('[GEMS_GAINED]', lang).replace('%1', '50'),
            },
            'date': date,
        }

    def translate_drop_chances(self, data: dict, lang):
        for key, item in data.copy().items():
            if not self.is_untranslated(key):
                continue
            new_key = _(key, lang)
            if key == '[KEYTYPE_5_TITLE]':
                new_key = f'{new_key}*'
            data[new_key] = item.copy()
            if key != new_key:
                del data[key]
            if isinstance(data[new_key], dict):
                self.translate_drop_chances(data[new_key], lang)

    def get_drop_chances(self, lang):
        drop_chances = self.drop_chances.copy()
        self.translate_drop_chances(drop_chances, lang)
        return drop_chances

    @staticmethod
    def get_shop_rewards(event, lang, emojis):
        event['shop_title'] = _('[SHOP]', lang)
        event['shop'] = []
        total_cost = 0
        total = _('[TOTAL]', lang)
        for shop_tier in event['shop_tiers']:
            if rewards := [
                _(r['name'], lang).replace('%1', str(r['amount']))
                for r in shop_tier['rewards']
            ]:
                total_cost += shop_tier['cost']
                currency = _(shop_tier['currency'], lang)
                if shop_tier['currency'] == '[GEMS]':
                    currency = emojis.get('gems')
                shop_display = f'**{_(shop_tier["title"], lang)}** ({shop_tier["cost"]} ' \
                               f'{currency}, {total} {total_cost}): ' \
                               f'{", ".join(rewards)}'
                event['shop'].append(shop_display)

    def get_event_rewards(self, event, lang):
        for stage, stage_reward in event['rewards'].items():
            stage_reward['name'] = _('[REWARD_N]', lang).replace('%1', str(stage))
            if EVENT_TYPES[event['type']] == '[RAIDBOSS]':
                if stage <= 2:
                    stage_reward['name'] = _('[MINIONS_N]').replace('%1', str(stage))
                else:
                    stage_reward['name'] = _('[PORTAL_N]', lang).replace('%1', str(stage - 2))

            for reward in stage_reward['rewards']:
                reward_type = reward['type']
                reward['type'] = _(reward_type, lang).replace('%1', '').strip()
                if reward_type == '[TITLE]':
                    reward['type'] += ' (' + _(f'[TITLE_{reward["data"]}]', lang) + ')'
                if reward_type == '[TROOP]':
                    reward['type'] = _(self.troops.get(reward['data'])['name'], lang)

    @staticmethod
    def get_event_medals(event, lang):
        for item in ('token', 'badge', 'medal'):
            if not event[item]:
                continue
            event[item] = {
                'name': _(f'[WONDER_{event[item]}_NAME]', lang),
                'description': _(f'[WONDER_{event[item]}_DESC]', lang),
            }

    def get_current_event(self, lang, emojis):
        event = copy.deepcopy(self.weekly_event)
        kingdoms = self.search_kingdom(event['kingdom_id'], lang)
        if kingdoms:
            event['kingdom'] = kingdoms[0]
        event['name'] = event['name'].get(lang, _(EVENT_TYPES[event['type']], lang))
        event['lore'] = event['lore'].get(lang, '')
        event['currencies'] = [{
            'name': currency['name'].get(lang, ''),
            'icon': currency['icon'],
            'value': _('[N_TIMES_POINTS]', lang).replace('%1', str(currency['value']))
        } for currency in event['currencies']]

        self.get_shop_rewards(event, lang, emojis)
        self.get_event_rewards(event, lang)
        self.get_event_medals(event, lang)

        def translate_restriction(title, restriction):
            if title == '[FILTER_MANACOLOR]':
                return emojis.get(COLORS[restriction])
            elif title == '[FILTER_ROLE]':
                return _(restriction, lang)
            elif title == '[KINGDOM]':
                return _(restriction, lang)
            elif title == '[TROOP_TYPES]':
                return _(f'[TROOPTYPE_{restriction.upper()}]', lang)
            """
            unknown, but possible restrictions:
                [FILTER_WEAPONTYPE]
                [RARITY]
                [ROSTER]
            """

        def translate_restrictions(title, restrictions):
            return [translated
                    for r in restrictions
                    if (translated := translate_restriction(title, r))]

        def translate_battle(b):
            result = b.copy()
            result['name'] = b['names'].get(lang)
            result['troops'] = []
            del result['names']
            for troop_id in b['ids']:
                troop = self.troops.get(troop_id).copy()
                self.translate_troop(troop, lang)
                result['troops'].append(troop)
            return result

        troop_restriction_types = (
            '[FILTER_MANACOLOR]', '[FILTER_ROLE]', '[KINGDOM]', '[RARITY]', '[ROSTER]', '[TROOP_TYPES]')
        event['troop_restrictions'] = {_(r, lang): ', '.join(translate_restrictions(r, v)) for r, v in
                                       event['restrictions'].items() if v and r in troop_restriction_types}
        weapon_restriction_types = ('[FILTER_MANACOLOR]', '[FILTER_WEAPONTYPE]', '[KINGDOM]')
        if EVENT_TYPES[event['type']] != '[TOWER_OF_DOOM]':
            event['weapon_restrictions'] = {_(r, lang): ', '.join(translate_restrictions(r, v)) for r, v in
                                            event['restrictions'].items() if v and r in weapon_restriction_types}
        event['troop'] = _(event['troop'], lang)
        if event['weapon_id']:
            event['weapon'] = _(self.weapons.get(event['weapon_id'], {'name': ''})['name'], lang)

        event['battles_title'] = _('[BATTLES]', lang)
        new_battles = []
        for battle in event['battles']:
            tb = translate_battle(battle)
            if tb['name'] and tb not in new_battles:
                new_battles.append(tb)
        event['battles'] = sorted(new_battles, key=operator.itemgetter('raw_rarity'), reverse=True)

        locale = translations.LANGUAGE_CODE_MAPPING.get(lang, lang)
        locale = translations.LOCALE_MAPPING.get(locale, 'en_GB') + '.UTF8'
        with calendar.different_locale(locale):
            event['formatted_start'] = event['start'].strftime(WEEK_DAY_FORMAT)
            event['formatted_end'] = event['end'].strftime(WEEK_DAY_FORMAT)

        return event

    def get_effects(self, lang):
        positive = _('[TROOPHELP_ALLPOSITIVESTATUSEFFECTS_1]', lang)
        negative = _('[TROOPHELP_ALLNEGATIVESTATUSEFFECTS_1]', lang)
        result = {
            positive: [],
            negative: [],
        }
        for effect in self.effects:
            key = positive if effect in self.positive_effects else negative
            result[key].append({
                'name': _(f'[TROOPHELP_{effect}_1]', lang),
                'description': _(f'[TROOPHELP_{effect}_2]', lang),
            })
        result[positive] = sorted(result[positive], key=operator.itemgetter('name'))
        result[negative] = sorted(result[negative], key=operator.itemgetter('name'))
        return result

    def get_active_gems(self, lang):
        result = []
        for gem in self.active_gems.values():
            active_gem = gem.copy()
            tutorial_key = f'[TUTORIAL_DESCRIPTION_{gem["tutorial"]}]'
            active_gem['tutorial'] = _(tutorial_key, lang)
            result.append(active_gem)
        return result

    @staticmethod
    def get_heroic_gems(lang):
        result = {}
        for gem, tutorial_id in GEM_TUTORIAL_IDS.items():
            if not tutorial_id:
                continue
            tutorial = _(f'[TUTORIAL_DESCRIPTION_{tutorial_id}]', lang)
            result.setdefault(tutorial, []).append(gem)
        return result

    @staticmethod
    def get_storms(lang):
        storms = {}
        fields = {
            '1': 'name',
            '2': 'description',
        }
        p = re.compile(r'\[TROOPHELP_STORM(\d+_?)+')
        for key, value in t.all_translations[lang].items():
            if not p.match(key):
                continue
            field = fields[key[-2]]
            storm_key = key[:-2]
            storms.setdefault(storm_key, {})[field] = value
        return storms

    def get_warbands(self, lang):
        warbands = [k.copy() for k in self.kingdoms.values()
                    if 'WARBAND' in k['reference_name']
                    and k['colors']
                    ]
        warband_teams = self.user_data['pEconomyModel']['WarbandTeams']
        available_warbands = [warband_teams[str(w)][0]['Data'] for w in self.user_data['pShopWarbandsData']]
        for warband in warbands:
            self.translate_kingdom(warband, lang)
            if ':' in warband['name']:
                warband['name'] = warband['name'].split(':')[1].strip()
            warband['available'] = ''
            if warband['id'] in available_warbands:
                warband['available'] = _('[AVAILABLE]', lang)
        return warbands

    def get_banners(self, lang):
        banners = [k.copy() for k in self.kingdoms.values() if k.get('colors')]
        for banner in banners:
            self.translate_kingdom(banner, lang)
        return sorted(banners, key=lambda x: x['banner']['name'])

    def get_map_data(self, lang, location):
        if not location:
            location = 'krystara'
        base_folder = 'Worldmap'
        map_data = {
            'krystara': {
                'title': _('[MAPNAME_MAIN]', lang),
                'map': f'{base_folder}/Main/Main_Albedo_full.png',
                'water': f'{base_folder}/Main/Water_Main_Albedo_full.png',
                'height': f'{base_folder}/Main/Main_Height_full.png',
                'blend_mode': 'overlay',
            },
            'underworld': {
                'title': _('[MAPNAME_UNDERWORLD]', lang),
                'map': f'{base_folder}/Underworld/Underworld_Albedo_full.png',
                'water': f'{base_folder}/Underworld/Water_Underworld_Albedo_full.png',
                'height': f'{base_folder}/Underworld/Underworld_Height_full.png',
                'blend_mode': 'stereo',
            }
        }
        result = map_data[location]
        result['kingdoms'] = []
        result['title'] = f"Gary's Gems of War Map: {result['title']}"

        def is_pseudo_kingdom(k):
            return k['location'] == 'krystara' and k['links'] == {-1}

        for kingdom in self.kingdoms.values():
            if 'description' not in kingdom:
                continue
            if kingdom['location'] != location:
                continue
            if is_pseudo_kingdom(kingdom):
                continue
            my_kingdom = kingdom.copy()
            self.translate_kingdom(my_kingdom, lang)
            if self.is_untranslated(my_kingdom['name']):
                continue
            result['kingdoms'].append(my_kingdom)
        return result

    def get_weekly_summary(self, lang, emojis):
        world_event = self.get_current_event(lang, emojis)

        def get_single_event(event_type, weekday):
            if filtered_events := [e for e in self.events
                                   if e['type'] == event_type
                                      and e['start_time'] >= world_event['start']
                                      and e['end_time'] <= world_event['end']
                                      and e['start_time'].weekday() == weekday
                                   ]:
                return self.translate_event(filtered_events[0], lang)
            else:
                return {'type': _(event_type, lang), 'start': datetime.datetime.utcnow() - datetime.timedelta(hours=24)}

        weekend_events = [e for e in self.events
                          if e['start_time'].weekday() == 4
                          and e['end_time'].weekday() == 0
                          and e['end_time'] == world_event['end']
                          ]
        extra_events = [
            self.translate_event(e, lang) for e in self.events if
            e['start_time'] == world_event['start'] and
            e['end_time'] == world_event['end'] and
            e['type'] != '[WEEKLY_EVENT]' and
            e['id'] != world_event['id']
        ]
        saturday_pet = [e for e in self.events if e['type'] == '[PETRESCUE]' and e['start_time'].weekday() == 5]
        if saturday_pet:
            saturday_pet = self.translate_event(saturday_pet[0], lang)

        glory_shops = [e for e in self.store_data.values() if e['tab'] == 'WeeklyEvent' and e['currency'] == '[GLORY]']
        glory_costs = None
        glory_rewards = []
        if glory_shops:
            glory_shop = glory_shops[0]
            glory_costs = glory_shop['cost']
            glory_rewards = [gw.copy() for gw in glory_shop['rewards']]
            for reward in glory_rewards:
                reward['name'] = _(reward['name'], lang)

        event_kingdom = self.search_kingdom(str(self.event_key_drops['kingdom_id']), lang)[0]
        event_mythics = [troop for troop in event_kingdom['troops']
                         if troop['raw_rarity'] == 'Mythic'
                         and 'release_date' not in troop
                         and 'Boss' not in troop['raw_types']
                         and troop['id'] not in SOULFORGE_ALWAYS_AVAILABLE]

        event_chest_drops = {
            'troops': event_mythics,
            'kingdom': event_kingdom,
        }

        result = {
            'world_event': world_event,
            'extra_events': extra_events,
            'class_trial': get_single_event('[CLASS_EVENT]', 3),
            'pet_rescue': get_single_event('[PETRESCUE]', 2),
            'saturday_pet': saturday_pet,
            'faction_assault': get_single_event('[DELVE_EVENT]', 1),
            'weekend': self.translate_event(weekend_events[0], lang) if weekend_events else None,
            'glory_cost': glory_costs,
            'glory_rewards': glory_rewards,
            'event_chest_drops': event_chest_drops,
            'world_event_title': _('[WEEKLY_EVENT]', lang),
            'restrictions_title': _('[TROOP_RESTRICTIONS]', lang),
            'event_keys_title': _('[KEYTYPE_3_TITLE]', lang),
            'today_weekday': (datetime.datetime.utcnow() + datetime.timedelta(
                hours=CONFIG.get('data_shift_hours'))).weekday(),
            'glory_shop_title': f'{_("[GLORY]", lang)} {_("[SHOP]", lang)}',
            'kingdom_title': _('[KINGDOM]', lang),
            'event_ended': _('[EVENT_HAS_ENDED]', lang),
            'medal': _('[REWARD_HELP_HEADING_MEDAL_2]', lang),
            'troop_title': _('[TROOP]', lang),
            'last_reward_points': _('[LAST_REWARD]', lang).format(),
            'weapon_title': _('[WEAPON]', lang),
        }
        return result

    def faction_summary(self, lang):
        factions = [k.copy() for k in self.kingdoms.values() if k['underworld'] and k['troop_ids']]
        [self.translate_kingdom(f, lang) for f in factions]
        return sorted(factions, key=operator.itemgetter('name'))

    def get_hoard_potions(self, lang):
        potions = [p.copy() for p in self.hoard_potions.values()]
        for potion in potions:
            potion['traits'] = self.enrich_traits(potion['traits'], lang, delve_id=potion['id'])
            potion['name'] = _(potion['name'], lang)
            potion['description'] = _(potion['description'], lang)
        return potions

    def translate_pet_rescue_stats(self, raw_stats, lang):
        total_rescues = sum(r['rescues'] for r in raw_stats)
        stats = []
        for row in raw_stats:
            pet = self.pets[row['pet_id']].translations[lang]
            amount = row['rescues']
            percentage = 100 * amount / total_rescues
            stats.append([pet, amount, percentage])
        return sorted(stats, key=operator.itemgetter(2, 1), reverse=True), total_rescues

    @staticmethod
    def get_dungeon_altars(lang):
        return [
            {
                'name': _(f'[DUNGEON_TITLE_ALTAR_{i}]', lang),
                'description': _(f'[DUNGEON_DESCRIPTION_ALTAR_{i}]', lang),
            }
            for i in range(7)
        ]

    @staticmethod
    def get_dungeon_traps(lang):
        return [
            {
                'name': _(f'[DUNGEON_TITLE_TRAP_{i}]', lang),
                'description': _(f'[DUNGEON_DESCRIPTION_TRAP_{i}]', lang),
            }
            for i in range(11)
        ]

    def get_orbs(self, lang):
        result = defaultdict(list)
        for orb in self.orbs.values():
            group_name = _(orb["group"], lang)
            result[group_name].append(
                {
                    'name': _(orb['name'], lang),
                    'help': _(orb['help'], lang).replace('%1', f'`{orb["data"]}`'),
                    'chance': f'{orb["chance"]:0.0%}',
                    'emoji': orb['emoji']
                }
            )
        return result

    def get_medals(self, lang):
        medal_id = 20000
        result = {
            'badges': [],
            'medals': [],
            'medals_title': _('[MEDALS]', lang),
            'badges_title': _('[REWARD_HELP_HEADING_MEDAL_1]', lang),
        }
        while True:
            if f'[WONDER_{medal_id}_NAME]' not in t.all_translations[lang]:
                break
            result['badges'].append({
                'name': _(f'[WONDER_{medal_id + 1}_NAME]', lang),
                'description': _(f'[WONDER_{medal_id + 1}_DESC]', lang)
            })
            result['medals'].append({
                'name': _(f'[WONDER_{medal_id + 2}_NAME]', lang),
                'description': _(f'[WONDER_{medal_id + 2}_DESC]', lang)
            })
            medal_id += 3
        result['badges'] = list(batched(result['badges'], 10))
        result['medals'] = list(batched(result['medals'], 10))
        return result
