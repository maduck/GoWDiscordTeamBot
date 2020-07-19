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


class TeamExpander:
    FORMAT = re.compile(r'(en|fr|de|ru|it|es|cn)?\[(\d+,?){1,13}\]', re.IGNORECASE)
    COLORS = ('blue', 'green', 'red', 'yellow', 'purple', 'brown')

    def __init__(self):
        self.troops = {}
        self.weapons = {}
        self.classes = {}
        self.banners = {}
        self.traits = {}
        self.talent_trees = {}
        self.translations = Translations()
        self.populate_world_data()

    def populate_world_data(self):
        with open('World.json', encoding='utf8') as f:
            data = json.load(f)

        for trait in data['Traits']:
            self.traits[trait['Code']] = trait['Name']
        for troop in data['Troops']:
            colors = [c.replace('Color', '').lower() for c, v in troop['ManaColors'].items() if v]
            self.troops[troop['Id']] = {
                'name': troop['Name'],
                'colors': sorted(colors),
                'description': troop['Description'],
                'spell_id': troop['SpellId'],
                'traits': [self.traits.get(trait, trait) for trait in troop['Traits']],
                'rarity': troop['TroopRarity'],
                'type': troop['TroopType'],
                'roles': troop['TroopRoleArray'],
            }
        for kingdom in data['Kingdoms']:
            color_lookup_names = [f'[GEM_{c.upper()}]' for c in self.COLORS]
            color_names = [self.translations.get(c).lower() for c in color_lookup_names]
            colors = zip(color_names, kingdom['BannerColors'])
            colors = sorted(colors, key=operator.itemgetter(1), reverse=True)
            self.banners[kingdom['Id']] = {
                'name': kingdom['BannerName'],
                'colors': colors,
            }
        for weapon in data['Weapons']:
            colors = [c.replace('Color', '').lower() for c, v in weapon['ManaColors'].items() if v]
            self.weapons[weapon['Id']] = {
                'name': f'[SPELL{weapon["SpellId"]}_NAME]',
                'colors': sorted(colors),
            }
        for tree in data['TalentTrees']:
            talents = [self.traits.get(trait, trait) for trait in tree['Traits']]
            self.talent_trees[tree['Code']] = talents
        for _class in data['HeroClasses']:
            self.classes[_class['Id']] = {
                'name': _class['Name'],
                'talents': [self.talent_trees[tree] for tree in _class['TalentTrees']]
            }

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

        for i in range(7 - len(result['talents'])):
            result['talents'].append(0)

        new_talents = []
        for talent_no, talent_code in enumerate(result['talents']):
            talent = '-'
            if talent_code > 0:
                talent = self.translations.get(result['class_talents'][talent_code - 1][talent_no], lang)
            new_talents.append(talent)
        result['talents'] = new_talents

        return result

    def get_team_from_message(self, message):
        code, lang = self.extract_code_from_message(message)
        if not code:
            return
        return self.get_team_from_code(code, lang)

    def search_troop(self, search_term, lang):
        result = None
        if search_term.isdigit():
            result = self.troops.get(int(search_term)).copy()
        else:
            for troop in self.troops.values():
                translated_name = self.translations.get(troop['name'], lang).lower().replace(' ', '')
                if search_term.lower().replace(' ', '') in translated_name:
                    result = troop.copy()
                    break
        if result:
            result['name'] = self.translations.get(result['name'], lang)
            result['color_code'] = "".join(result['colors'])
        return result


