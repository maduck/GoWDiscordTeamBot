import copy
import datetime
import importlib
import logging
import operator
import re
from calendar import different_locale

import translations
from data_source.game_data import GameData
from game_constants import COLORS, EVENT_TYPES, GEM_TUTORIAL_IDS, RARITY_COLORS, SOULFORGE_REQUIREMENTS, TROOP_RARITIES, \
    UNDERWORLD_SOULFORGE_REQUIREMENTS, WEAPON_RARITIES
from models.bookmark import Bookmark
from models.toplist import Toplist
from util import dig, extract_search_tag, get_next_monday_in_locale, translate_day

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
    importlib.reload(translations)
    try:
        del _
    except NameError:
        pass
    _ = translations.Translations().get


class TeamExpander:

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
        self.reroll_tasks = world.campaign_rerolls
        self.soulforge = world.soulforge
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

        for i, element in enumerate(code):
            troop = self.troops.get(element)
            weapon = self.weapons.get(element)
            if troop:
                troop = troop.copy()
                self.translate_troop(troop, lang)
                result['troops'].append(troop)
                continue
            elif weapon:
                weapon = weapon.copy()
                self.translate_weapon(weapon, lang)
                result['troops'].append(weapon)
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
            if i <= 3:
                result['troops'].append(self.troops['`?`'])
                continue
            elif i == 4:
                banner = {
                    'colors': [('questionmark', 1)],
                    'name': '[REQUIREMENTS_NOT_MET]',
                    'filename': 'Locked',
                    'id': '`?`'
                }
                result['banner'] = self.translate_banner(banner, lang)
                continue
            elif i == 12:
                result['class'] = _('[REQUIREMENTS_NOT_MET]', lang)
                result['talents'] = []
                has_class = True
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

    @staticmethod
    def search_item(search_term, lang, items, lookup_keys, translator, sort_by='name'):
        if search_term.isdigit() and int(search_term) in items:
            item = items.get(int(search_term))
            if item:
                result = item.copy()
                translator(result, lang)
                return [result]
            return []
        possible_matches = []
        for base_item in items.values():
            if base_item['name'] == '`?`' or base_item['id'] == '`?`':
                continue
            item = base_item.copy()
            translator(item, lang)
            lookups = {
                k: extract_search_tag(dig(item, k)) for k in lookup_keys
            }
            real_search = extract_search_tag(search_term)

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
        ]
        return self.search_item(search_term, lang,
                                items=self.troops,
                                lookup_keys=lookup_keys,
                                translator=self.translate_troop)

    def translate_troop(self, troop, lang):
        troop['name'] = _(troop['name'], lang)
        if self.is_untranslated(troop['name']):
            troop['name'] = troop['reference_name']
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
        reference_name = troop['kingdom'].get('reference_name', troop['kingdom']['name'])
        troop['kingdom'] = _(troop['kingdom']['name'], lang)
        if self.is_untranslated(troop['kingdom']):
            troop['kingdom'] = reference_name
        troop['spell'] = self.translate_spell(troop['spell_id'], lang)
        troop['spell_title'] = _('[TROOPHELP_SPELL0]', lang)
        self.translate_traitstones(troop, lang)
        troop['bonuses_title'] = _('[BONUSES]', lang)

    @staticmethod
    def translate_traitstones(item, lang):
        item['traitstones_title'] = _('[SOULFORGE_TAB_TRAITSTONES]', lang)
        if 'traitstones' not in item:
            item['traitstones'] = []
        traitstones = []
        for rune in item['traitstones']:
            traitstones.append(f'{_(rune["name"], lang)} ({rune["amount"]})')
        item['traitstones'] = traitstones

    @staticmethod
    def enrich_traits(traits, lang):
        new_traits = []
        for trait in traits:
            new_trait = trait.copy()
            new_trait['name'] = _(trait['name'], lang)
            new_trait['description'] = _(trait['description'], lang)
            new_traits.append(new_trait)
        return new_traits

    def search_kingdom(self, search_term, lang, include_warband=True):
        lookup_keys = ['name']
        return self.search_item(search_term, lang, items=self.kingdoms, lookup_keys=lookup_keys,
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
            translated_talents = []
            for talent in tree:
                translated_talents.append({
                    'name': _(talent['name'], lang),
                    'description': _(talent['description'], lang)
                })
            translated_trees.append(translated_talents)
        self.translate_traitstones(_class, lang)
        _class['talents_title'] = _('[TALENT_TREES]', lang)
        _class['kingdom_title'] = _('[KINGDOM]', lang)
        _class['traits_title'] = _('[TRAITS]', lang)
        _class['traits'] = self.enrich_traits(_class['traits'], lang)
        _class['weapon_title'] = _('[WEAPON]', lang)
        _class['talents'] = translated_trees
        _class['trees'] = [_(f'[TALENT_TREE_{t.upper()}]', lang) for t in _class['trees']]
        _class['type_short'] = _(f'[TROOPTYPE_{_class["type"].upper()}]', lang)
        _class['type'] = _(f'[PERK_TYPE_{_class["type"].upper()}]', lang)
        _class['weapon_bonus'] = _('[MAGIC_BONUS]', lang) + " " + _(
            f'[MAGIC_BONUS_{COLORS.index(_class["weapon_color"])}]', lang)

    def search_talent(self, search_term, lang):
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
        return sorted(possible_matches, key=operator.itemgetter('name'))

    @staticmethod
    def translate_talent_tree(tree, lang):
        tree['talents_title'] = _('[TALENT_TREES]', lang)
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

    def get_troops_with_trait(self, trait, lang):
        return self.get_objects_by_trait(trait, self.troops, self.translate_troop, lang)

    def get_classes_with_trait(self, trait, lang):
        return self.get_objects_by_trait(trait, self.classes, self.translate_class, lang)

    @staticmethod
    def get_objects_by_trait(trait, objects, translator, lang):
        result = []
        for o in objects.values():
            trait_codes = [t['code'] for t in o['traits']] if 'traits' in o else []
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
            for i, amount in enumerate(upgrade):
                if amount:
                    upgrades.append(
                        {'name': f'{upgrade_titles[i]} {bonus_title}',
                         'description': f'+{amount} {upgrade_titles[i]}'})

        weapon['upgrades'] = upgrades + [self.translate_spell(spell['id'], lang) for spell in weapon['affixes']]
        weapon['kingdom_title'] = _('[KINGDOM]', lang)
        weapon['kingdom_id'] = weapon['kingdom']['id']
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
            amount = sum([t['amount'] for t in self.troops[troop_id]['traitstones'] if t['id'] == traitstone['id']])
            troops.append([_(self.troops[troop_id]['name'], lang), amount])
        traitstone['troops'] = sorted(troops, key=operator.itemgetter(1), reverse=True)

        classes = []
        for class_id in traitstone['class_ids']:
            amount = sum([t['amount'] for t in self.classes[class_id]['traitstones'] if t['id'] == traitstone['id']])
            classes.append([_(self.classes[class_id]['name'], lang), amount])
        traitstone['classes'] = classes

        kingdoms = []
        for kingdom_id in traitstone['kingdom_ids']:
            kingdoms.append(_(self.kingdoms[int(kingdom_id)]['name'], lang))
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
            number_of_replacements = len(re.findall(r'\{\d\}', description))
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

        boost = ''
        if spell['boost'] and spell['boost'] > 100:
            boost = f' [x{int(round(spell["boost"] / 100))}]'
        elif spell['boost'] and spell['boost'] != 1 and spell['boost'] <= 100:
            boost = f' [{100 / spell["boost"]:0.0f}:1]'

        description = f'{description}{boost}'

        return {
            'name': _(spell['name'], lang),
            'cost': spell['cost'],
            'description': description,
        }

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

        for kingdom_id in self.event_kingdoms:
            end = start + datetime.timedelta(days=7)
            if kingdom_id != 0:
                event_data = {
                    'start': start,
                    'end': end,
                    'kingdom': _(self.kingdoms[kingdom_id]['name'], lang,
                                 default=self.kingdoms[kingdom_id]['reference_name']),
                }
                result[start] = event_data
            start = end
        return sorted(result.values(), key=operator.itemgetter('start'))

    def guess_weekly_kingdom_from_troop_spoilers(self, lang):
        result = {}
        latest_date = datetime.datetime.utcnow()
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
        events = [self.translate_event(e, lang) for e in self.events if today <= e['start']]
        return events

    def translate_event(self, event, lang):
        entry = event.copy()

        entry['extra_info'] = ''
        if entry['type'] in ('[BOUNTY]', '[HIJACK]') and entry['gacha'] and entry['gacha'] in self.troops:
            entry['extra_info'] = _(self.troops[entry['gacha']]['name'], lang)
        elif entry['type'] == '[PETRESCUE]' and entry['gacha']:
            entry['extra_info'] = self.pets[entry['gacha']][lang].name
        elif entry['type'] == '[CLASS_EVENT]' and entry['gacha']:
            entry['extra_info'] = _(self.classes[entry['gacha']]['name'], lang)
        elif entry['type'] == '[TOWER_OF_DOOM]' and entry['gacha']:
            entry['extra_info'] = _(self.troops[entry['gacha']]['name'], lang)
        elif entry['type'] == '[DELVE_EVENT]':
            entry['extra_info'] = _(self.kingdoms[entry['kingdom_id']]['name'], lang,
                                    default=self.kingdoms[entry['kingdom_id']]['reference_name'])
        elif entry['type'] == '[HIJACK]' and entry['troops']:
            entry['extra_info'] = ', '.join(_(self.troops[t]['name'], lang) for t in entry['troops'])
        elif entry['type'] == '[INVASION]' and entry['gacha'] and entry['gacha'] in self.troops:
            troop = self.troops[entry['gacha']]
            troop_name = _(troop['name'], lang)
            troop_types = [_(f'[TROOPTYPE_{t.upper()}]', lang) for t in troop['types']]
            entry['extra_info'] = f'{troop_name} ({", ".join(troop_types)})'
        elif entry['type'] in ('[WEEKLY_EVENT]', '[RARITY_5]') and entry['gacha'] and entry['gacha'] in self.troops:
            troop = self.troops[entry['gacha']]
            troop_name = _(troop['name'], lang)
            kingdom = _(self.kingdoms[entry['kingdom_id']]['name'], lang,
                        default=self.kingdoms[entry['kingdom_id']]['reference_name'])
            entry['extra_info'] = f'{troop_name} ({kingdom})'
            entry['kingdom'] = kingdom

        if entry['kingdom_id']:
            kingdom = _(self.kingdoms[entry['kingdom_id']]['name'], lang)
            entry['kingdom'] = kingdom

        locale = translations.LANGUAGE_CODE_MAPPING.get(lang, lang)
        locale = translations.LOCALE_MAPPING.get(locale, 'en_GB') + '.UTF8'
        with different_locale(locale):
            entry['formatted_start'] = entry['start'].strftime('%b %d')
            entry['start_day'] = entry['start'].strftime('%A')
            entry['formatted_end'] = entry['end'].strftime('%b %d')
            entry['end_day'] = entry['end'].strftime('%A')

        entry['raw_type'] = entry['type']
        entry['type'] = _(entry['type'], lang)

        return entry

    def get_campaign_tasks(self, lang, _filter=None):
        result = {'heading': f'{_("[CAMPAIGN]", lang)}: {_("[TASKS]", lang)}'}
        tiers = ['bronze', 'silver', 'gold']
        result['campaigns'] = {
            f'[MEDAL_LEVEL_{i}]': [self.translate_campaign_task(t, lang) for t in self.campaign_tasks[tier]]
            for i, tier in reversed(list(enumerate(tiers))) if _filter is None or tier.lower() == _filter.lower()
        }
        formatted_start, start_date = get_next_monday_in_locale(date=None, lang=lang)
        result['has_content'] = any([len(c) > 0 for c in result['campaigns'].values()])
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
        tasks = {
            f'[MEDAL_LEVEL_{i}]': [self.translate_campaign_task(t, lang) for t in self.reroll_tasks[tier]]
            for i, tier in reversed(list(enumerate(tiers))) if _filter is None or tier.lower() == _filter.lower()
        }
        return tasks

    def translate_campaign_task(self, task, lang):
        new_task = task.copy()
        color_code = int(new_task['value1']) if new_task['value1'].isdigit() else 666
        color = COLORS[color_code].upper() if color_code < len(COLORS) else '`?`'
        if isinstance(new_task.get('y'), str):
            new_task['y'] = _(f'[{new_task["y"].upper()}]', lang)
        new_task['plural'] = int(new_task.get('x', 1)) != 1

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
        new_task['title'] = _(new_task['title'], lang, plural=new_task['plural'])
        new_task['name'] = _(new_task["name"], lang, plural=new_task['plural'])

        if '{0}' not in new_task['name'] and '{2}' not in new_task['name']:
            new_task['name'] = f'{task["x"]}x ' + new_task['name']

        for before, after in replacements.items():
            if before in new_task['title'] or before in new_task['name']:
                translated = _(after.format(**new_task).format(self.troops), lang, plural=new_task['plural'])
                if '`?`' in translated:
                    translated = '`?`'
                new_task['title'] = new_task['title'].replace(before, translated)
                new_task['name'] = new_task['name'].replace(before, translated)

        where = ''
        if new_task['value1'] == '`?`':
            pass
        elif task['name'] == '[TASK_KILL_TROOP_COLOR]':
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

        new_task['name'] += where

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
        # FIXME this is transitional until all new models are in place.
        if spoiler['type'] in ['pet']:
            item = getattr(self, spoiler['type'] + 's').get(spoiler['id'])
            if not item:
                return
            entry = item[translations.LANGUAGE_CODE_MAPPING.get(lang, lang)].data.copy()
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

        kingdom_id = entry.get('kingdom_id')
        if kingdom_id:
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

    @staticmethod
    def translate_recipe(recipe, lang):
        new_recipe = recipe.copy()
        new_recipe['name'] = _(recipe['name'], lang)
        rarity_number = WEAPON_RARITIES.index(new_recipe['rarity'])
        new_recipe['rarity_number'] = rarity_number
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
            return result

        translated = [try_different_translated_versions_because_devs_are_stupid(c) for c in categories]
        return dict(zip(categories, translated))

    def get_levels(self, lang):
        levels = [{
            'level': level['level'],
            'bonus': _(level['bonus'], lang),
        } for level in self.levels]
        return levels

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
        toplist = self.translate_toplist(toplist_id, lang)

        return toplist

    def kingdom_percentage(self, filter_name, filter_values, lang):
        result = {}
        now = datetime.datetime.utcnow()
        hidden_kingdoms = [3032, 3033, 3034, 3038]

        for filter_ in filter_values:
            kingdoms = []
            for kingdom in self.kingdoms.values():
                if kingdom['location'] != 'krystara':
                    continue
                if kingdom['id'] in hidden_kingdoms:
                    continue
                all_troops = [self.troops.get(t) for t in kingdom['troop_ids']]
                available_troops = [t for t in all_troops if t and t.get('release_date', now) <= now]
                if not available_troops:
                    continue
                fitting_troops = [t for t in available_troops if filter_ in t[filter_name]]
                kingdoms.append({
                    'name': _(kingdom['name'], lang),
                    'total': len(available_troops),
                    'fitting_troops': len(fitting_troops),
                    'percentage': len(fitting_troops) / len(available_troops),
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
        result = []
        for adventure in self.adventure_board:
            result.append(self.translate_adventure(adventure, lang))
        return result

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
        if not param:
            return True
        return param[0] + param[-1] == '[]'

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
        alternate_kingdom = None
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
        result = {
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
            'stat_increases': {'attack': sum(weapon['attack_increase']),
                               'health': sum(weapon['health_increase']),
                               'armor': sum(weapon['armor_increase']),
                               'magic': sum(weapon['magic_increase'])},
            'stat_icon': 'Atlas/{stat}.png',
            'texts': {
                'from_battles': _('[PET_LOOT_BONUS]', lang).replace('+%1% %2 ', '').replace('+%1 %2 ', ''),
                'gem_bounty': _('[DUNGEON_OFFER_NAME]', lang),
                'kingdom_challenges': f'{_("[KINGDOM]", lang)} {_("[CHALLENGES]", lang)}',
                'soulforge': _('[SOULFORGE]', lang),
                'resources': _('[RESOURCES]', lang),
                'dungeon': _('[DUNGEON]', lang),
                'dungeon_battles': _('[TASK_WIN_DUNGEON_BATTLES]', lang).replace('{0}', '3').replace('\x19', 's'),
                'tier_8': _('[CHALLENGE_TIER_8_ROMAN]', lang),
                'available': _('[AVAILABLE]', lang),
                'in_soulforge': in_soulforge_text,
                'n_gems': _('[GEMS_GAINED]', lang).replace('%1', '50'),
            },
            'date': date,
        }
        return result

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

        for stage in event['rewards'].keys():
            for reward in event['rewards'][stage]['rewards']:
                reward_type = reward['type']
                reward['type'] = _(reward_type, lang).replace('%1', '').strip()
                if reward_type == '[TITLE]':
                    reward['type'] += ' (' + _(f'[TITLE_{reward["data"]}]', lang) + ')'
                if reward_type == '[TROOP]':
                    reward['type'] = _(self.troops.get(reward['data'])['name'], lang)

        event['shop_title'] = _('[SHOP]', lang)
        event['shop'] = []
        for shop_tier in event['shop_tiers']:
            rewards = [_(k, lang).replace('%1', str(v)) for k, v in shop_tier['rewards'].items()]
            if rewards:
                shop_display = f'**{_(shop_tier["title"], lang)}** ({shop_tier["cost"]} ' \
                               f'{_(shop_tier["currency"], lang)}): ' \
                               f'{", ".join(rewards)}'
                event['shop'].append(shop_display)

        for item in ('token', 'badge', 'medal'):
            if not event[item]:
                continue
            event[item] = {
                'name': _(f'[WONDER_{event[item]}_NAME]', lang),
                'description': _(f'[WONDER_{event[item]}_DESC]', lang),
            }

        def translate_restriction(title, restriction):
            if title == '[FILTER_MANACOLOR]':
                return emojis.get(COLORS[restriction])
            elif title == '[FILTER_ROLE]':
                pass
            elif title == '[FILTER_WEAPONTYPE]':
                pass
            elif title == '[KINGDOM]':
                return _(restriction, lang)
            elif title == '[RARITY]':
                pass
            elif title == '[ROSTER]':
                pass
            elif title == '[TROOP_TYPES]':
                return _(f'[TROOPTYPE_{restriction.upper()}]', lang)

        def translate_restrictions(title, restrictions):
            result = []
            for r in restrictions:
                translated = translate_restriction(title, r)
                if translated:
                    result.append(translated)
            return result

        def translate_battle(b):
            result = b.copy()
            result['name'] = b['names'].get(lang)
            del result['names']
            return result

        event['restrictions'] = {_(r, lang): ', '.join(translate_restrictions(r, v)) for r, v in
                                 event['restrictions'].items() if v}
        event['troop'] = _(event['troop'], lang)
        if event['weapon_id']:
            event['weapon'] = _(self.weapons.get(event['weapon_id'], {'name': ''})['name'], lang)

        new_battles = []
        for battle in event['battles']:
            tb = translate_battle(battle)
            if tb not in new_battles:
                new_battles.append(tb)
        event['battles'] = new_battles

        locale = translations.LANGUAGE_CODE_MAPPING.get(lang, lang)
        locale = translations.LOCALE_MAPPING.get(locale, 'en_GB') + '.UTF8'
        with different_locale(locale):
            event['formatted_start'] = event['start'].strftime('%b %d')
            event['formatted_end'] = event['end'].strftime('%b %d')

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
        for key, value in t.translations[lang].items():
            if not p.match(key):
                continue
            field = fields[key[-2]]
            storm_key = key[:-2]
            storms.setdefault(storm_key, {})[field] = value
        return storms

    def get_warbands(self, lang):
        warbands = [k.copy() for k in self.kingdoms.values() if 'WARBAND' in k['reference_name']]
        for warband in warbands:
            self.translate_kingdom(warband, lang)
        return warbands

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
            filtered_events = [e for e in self.events if
                               e['type'] == event_type and
                               e['start_time'] >= world_event['start'] and
                               e['end_time'] <= world_event['end'] and
                               e['start_time'].weekday() == weekday
                               ]
            if filtered_events:
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
            e['type'] != '[WEEKLY_EVENT]'
        ]
        glory_troops = [e for e in self.store_data.values() if
                        e['tab'] == 'WeeklyEvent' and e['currency'] == '[GLORY]']
        saturday_pet = [e for e in self.events if e['type'] == '[PETRESCUE]' and e['start_time'].weekday() == 5]
        if saturday_pet:
            saturday_pet = self.translate_event(saturday_pet[0], lang)
        glory_troop = self.troops['`?`']
        if glory_troops and 'troop_id' in glory_troops[0]['rewards']:
            glory_troop = self.search_troop(str(glory_troops[0]['rewards']['troop_id']), lang)[0]

        event_kingdom = self.search_kingdom(str(self.event_key_drops['kingdom_id']), lang)[0]
        event_mythics = [t for t in event_kingdom['troops']
                         if t['raw_rarity'] == 'Mythic'
                         and 'release_date' not in t
                         and 'Boss' not in t['raw_types']]

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
            'glory_troop': glory_troop,
            'event_chest_drops': event_chest_drops,
            'world_event_title': _('[WEEKLY_EVENT]', lang),
            'restrictions_title': _('[TROOP_RESTRICTIONS]', lang),
            'event_keys_title': _('[KEYTYPE_3_TITLE]', lang),
            'today_weekday': datetime.datetime.utcnow().weekday(),
            'glory_shop_title': f'{_("[GLORY]", lang)} {_("[SHOP]", lang)}',
            'kingdom_title': _('[KINGDOM]', lang),
            'event_ended': _('[EVENT_HAS_ENDED]', lang),
            'medal': _('[REWARD_HELP_HEADING_MEDAL_2]', lang),
        }
        return result

    def faction_summary(self, lang):
        factions = [k.copy() for k in self.kingdoms.values() if k['underworld'] and k['troop_ids']]
        [self.translate_kingdom(f, lang) for f in factions]
        return sorted(factions, key=operator.itemgetter('name'))
