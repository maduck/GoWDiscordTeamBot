import datetime
import operator
import re

from game_assets import GameAssets
from game_constants import COLORS, EVENT_TYPES, SOULFORGE_ALWAYS_AVAILABLE
from util import convert_color_array

NO_TRAIT = {'code': '', 'name': '[TRAIT_NONE]', 'description': '[TRAIT_NONE_DESC]'}


class U(str):
    def __format__(self, fmt):
        if not fmt:
            s = str(self)
        elif fmt[0] == 'u':
            s = self.upper()
            fmt = fmt[1:]
        elif fmt[0] == 'l':
            s = self.lower()
            fmt = fmt[1:]
        else:
            s = str(self)
        return s.__format__(fmt)


class GameData:

    def __init__(self):
        self.data = None
        self.user_data = {
            'pEconomyModel': {
                'TroopReleaseDates': [],
                'KingdomReleaseDates': [],
                'HeroClassReleaseDates': [],
                'PetReleaseDates': [],
                'RoomReleaseDates': [],
                'WeaponReleaseDates': [],
                'BasicLiveEventArray': [],
            }
        }

        self.troops = {'`?`': {'name': '`?`'}}
        self.spells = {}
        self.weapons = {}
        self.classes = {}
        self.banners = {}
        self.traits = {}
        self.kingdoms = {}
        self.pet_effects = ()
        self.pets = {}
        self.talent_trees = {}
        self.spoilers = []
        self.events = []
        self.soulforge_weapons = []
        self.campaign_tasks = {}
        self.campaign_data = {}
        self.soulforge = {}
        self.soulforge_raw_data = {}
        self.traitstones = {}
        self.levels = []
        self.adventure_board = []

    def read_json_data(self):
        self.data = GameAssets.load('World.json')
        self.user_data = GameAssets.load('User.json')
        if GameAssets.exists('Campaign.json'):
            self.campaign_data = GameAssets.load('Campaign.json')
        if GameAssets.exists('Soulforge.json'):
            self.soulforge_raw_data = GameAssets.load('Soulforge.json')

    def populate_world_data(self):
        self.read_json_data()

        self.populate_spells()
        self.populate_traits()
        self.populate_troops()
        self.populate_kingdoms()
        self.populate_weapons()
        self.populate_pets()
        self.populate_talents()
        self.populate_classes()
        self.populate_release_dates()
        self.enrich_kingdoms()
        self.populate_campaign_tasks()
        self.populate_soulforge()
        self.populate_traitstones()
        self.populate_hero_levels()
        self.populate_max_power_levels()
        self.populate_adventure_board()

    def populate_classes(self):
        for _class in self.data['HeroClasses']:
            self.classes[_class['Id']] = {
                'id': _class['Id'],
                'name': _class['Name'],
                'code': _class['Code'],
                'talents': [self.talent_trees[tree]['talents'] for tree in _class['TalentTrees']],
                'trees': _class['TalentTrees'],
                'traits': [self.traits.get(trait, NO_TRAIT) for trait in
                           _class['Traits']],
                'weapon_id': _class['ClassWeaponId'],
                'kingdom_id': _class['KingdomId'],
                'type': _class['Augment'][0],
                'magic_color': _class['BonusColor'],
                'weapon_color': _class['BonusWeapon'],
            }
            self.weapons[_class['ClassWeaponId']]['class'] = _class['Name']
            for tree in _class['TalentTrees']:
                self.talent_trees[tree]['classes'].append(self.classes[_class['Id']].copy())
            self.kingdoms[_class['KingdomId']]['class_id'] = _class['Id']

    def populate_talents(self):
        for tree in self.data['TalentTrees']:
            talents = [self.traits.get(trait, trait) for trait in tree['Traits']]
            self.talent_trees[tree['Code']] = {
                'name': f'[TALENT_TREE_{tree["Code"].upper()}]',
                'talents': talents,
                'classes': [],
            }

    def populate_pets(self):
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
        for pet in self.data['Pets']:
            colors = convert_color_array(pet)
            self.pets[pet['Id']] = {
                'id': pet['Id'],
                'name': pet['Name'],
                'kingdom_id': pet['KingdomId'],
                'kingdom': self.kingdoms[pet['KingdomId']],
                'colors': sorted(colors),
                'effect': self.pet_effects[pet['Effect']],
                'effect_data': pet.get('EffectData'),
                'troop_type': pet.get('EffectTroopType'),
                'filename': pet['FileBase'],
            }

    def populate_weapons(self):
        for weapon in self.data['Weapons']:
            colors = convert_color_array(weapon)
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
                'armor_increase': weapon['ArmorIncrease'],
                'attack_increase': weapon['AttackIncrease'],
                'health_increase': weapon['HealthIncrease'],
                'magic_increase': weapon['SpellPowerIncrease'],
                'affixes': [self.spells.get(spell) for spell in weapon['Affixes'] if spell in self.spells],
            }
            self.kingdoms[weapon['KingdomId']]['weapon_ids'].append(weapon['Id'])

    def populate_kingdoms(self):
        for kingdom in self.data['Kingdoms']:
            colors = [f'[GEM_{c.upper()}]' for c in COLORS]
            colors = zip(colors, kingdom['BannerColors'])
            colors = sorted(colors, key=operator.itemgetter(1), reverse=True)
            self.banners[kingdom['Id']] = {
                'id': kingdom['Id'],
                'name': kingdom['BannerName'],
                'colors': colors,
                'filename': kingdom['FileBase'],
            }
            kingdom_troops = [troop_id for troop_id in kingdom['TroopIds'] if troop_id != -1]
            kingdom_colors = convert_color_array(kingdom)
            self.kingdoms[kingdom['Id']] = {
                'id': kingdom['Id'],
                'name': kingdom['Name'],
                'description': kingdom['Description'],
                'punchline': kingdom['ByLine'],
                'underworld': bool(kingdom.get('MapIndex', 0)),
                'location': self.infer_kingdom_location(kingdom),
                'troop_ids': kingdom_troops,
                'weapon_ids': [],
                'troop_type': kingdom['KingdomTroopType'],
                'linked_kingdom_id': kingdom.get('SisterKingdomId'),
                'colors': sorted(kingdom_colors),
                'filename': kingdom['FileBase'],
            }
            if 'SisterKingdomId' in kingdom:
                self.kingdoms[kingdom['SisterKingdomId']]['linked_kingdom_id'] = kingdom['Id']
            for troop_id in kingdom_troops:
                self.troops[troop_id]['kingdom'] = kingdom

    @staticmethod
    def infer_kingdom_location(kingdom):
        if 'WARBAND' in kingdom['ReferenceName']:
            return 'warband'
        return 'underworld' if bool(kingdom.get('MapIndex', 0)) else 'krystara'

    def populate_troops(self):
        for troop in self.data['Troops']:
            colors = convert_color_array(troop)
            self.troops[troop['Id']] = {
                'id': troop['Id'],
                'name': troop['Name'],
                'colors': sorted(colors),
                'description': troop['Description'],
                'spell_id': troop['SpellId'],
                'traits': [self.traits.get(trait, NO_TRAIT) for trait in
                           troop['Traits']],
                'rarity': troop['TroopRarity'],
                'types': [troop['TroopType']],
                'roles': troop['TroopRoleArray'],
                'kingdom': {'Name': ''},
                'filename': troop['FileBase'],
                'armor': sum(troop['ArmorIncrease']),
                'health': sum(troop['HealthIncrease']),
                'magic': sum(troop['SpellPowerIncrease']),
                'attack': sum(troop['AttackIncrease']),
            }
            if 'TroopType2' in troop:
                self.troops[troop['Id']]['types'].append(troop['TroopType2'])

    def populate_traits(self):
        for trait in self.data['Traits']:
            self.traits[trait['Code']] = {
                'code': trait['Code'],
                'name': trait['Name'],
                'description': trait['Description'],
                'image': trait['Image'],
            }

    def populate_spells(self):
        for spell in self.data['Spells']:
            spell_effects = []
            boost = 0
            last_type = ""
            for step in spell['SpellSteps']:
                if 'Type' in step and 'SpellPowerMultiplier' in step:
                    amount = step.get('Amount', 0)
                    multiplier = step.get('SpellPowerMultiplier', 1)
                    if last_type != step['Type']:
                        spell_effects.append([multiplier, amount])
                        last_type = step['Type']
                elif step['Type'].startswith('Count'):
                    boost = step.get('Amount', 1)
            self.spells[spell['Id']] = {
                'id': spell['Id'],
                'name': spell['Name'],
                'description': spell['Description'],
                'cost': spell['Cost'],
                'effects': spell_effects,
                'boost': boost,
            }

    def get_current_event_kingdom_id(self):
        today = datetime.date.today()
        weekly_events = [e for e in self.events
                         if e['end'] - e['start'] == datetime.timedelta(days=7)
                         and e['start'] <= today <= e['end']
                         and e['start'].weekday() == 0
                         and e['kingdom_id']
                         and e['type'] == '[WEEKLY_EVENT]']
        if not weekly_events:
            return 3000
        event_kingdom_id = weekly_events[0]['kingdom_id']
        return int(event_kingdom_id)

    def populate_campaign_tasks(self):
        event_kingdom_id = self.get_current_event_kingdom_id()

        tasks = self.user_data['pTasksData']['CampaignTasks'][str(event_kingdom_id)]
        for level in ('Bronze', 'Silver', 'Gold'):
            task_list = [self.transform_campaign_task(task) for task in tasks[level]]
            self.campaign_tasks[level.lower()] = sorted(task_list, key=operator.itemgetter('order'))

    def transform_campaign_task(self, task):
        extra_data = {}
        m = re.match(r'Campaign_(?P<kingdom_id>\d+)_(?P<level>.+)_(?P<order>\d+)', task['Id'])
        task_id = m.groupdict()
        task_order = 1000 + int(task_id['order'])
        kingdom_id = int(task_id['kingdom_id'])
        level = task_id['level']

        for i, t in enumerate(self.campaign_data.get(f'Campaign{level}', [])):
            if t and t['Id'] == task['Id']:
                extra_data = t
                task_order = i

        translated_task = {
            'reward': task['Rewards'][0]['Amount'],
            'condition': task.get('Condition'),
            'order': task_order,
            'task': task['Task'],
            'name': task['TaskName'],
            'title': task['TaskTitle'],
            'tags': task['Tag'].split(','),
            'x': task.get('XValue'),
            'y': task.get('YValue'),
            'value0': U(extra_data.get('Value0', '`?`')),
            'value1': U(extra_data.get('Value1', '`?`')),
            'c': U(task.get('CValue')),
            'd': U(task.get('DValue')),
            'kingdom_id': kingdom_id,
            'orig': task,
        }

        return translated_task

    @staticmethod
    def get_datetime(val):
        date_format = '%m/%d/%Y %I:%M:%S %p %Z'
        return datetime.datetime.strptime(val, date_format)

    def populate_release_dates(self):
        release: dict
        for release in self.user_data['pEconomyModel']['TroopReleaseDates']:
            troop_id = release['TroopId']
            release_date = self.get_datetime(release['Date'])
            if troop_id in self.troops:
                self.troops[troop_id]['release_date'] = release_date
                self.spoilers.append({'type': 'troop', 'date': release_date, 'id': troop_id})
                if self.troops[troop_id]['rarity'] == 'Mythic' and 'Id' in self.troops[troop_id]['kingdom']:
                    self.events.append(
                        {'start': release_date.date(),
                         'end': release_date.date() + datetime.timedelta(days=7),
                         'type': '[RARITY_5]',
                         'names': self.troops[troop_id]['name'],
                         'gacha': troop_id,
                         'kingdom_id': self.troops[troop_id]['kingdom']['Id']}
                    )
        for release in self.user_data['pEconomyModel']['PetReleaseDates']:
            pet_id = release['PetId']
            release_date = self.get_datetime(release['Date'])
            if pet_id in self.pets:
                self.pets[pet_id]['release_date'] = release_date
                self.spoilers.append({'type': 'pet', 'date': release_date, 'id': pet_id})
        for release in self.user_data['pEconomyModel']['KingdomReleaseDates']:
            kingdom_id = release['KingdomId']
            release_date = self.get_datetime(release['Date'])
            if kingdom_id in self.kingdoms:
                self.kingdoms[kingdom_id]['release_date'] = release_date
                self.spoilers.append({'type': 'kingdom', 'date': release_date, 'id': kingdom_id})
        for release in self.user_data['pEconomyModel']['HeroClassReleaseDates']:
            class_id = release['QuestId']
            release_date = self.get_datetime(release['Date'])
            if class_id in self.classes:
                self.classes[class_id]['release_date'] = release_date
                self.spoilers.append({'type': 'class', 'date': release_date, 'id': class_id})
        for release in self.user_data['pEconomyModel']['RoomReleaseDates']:
            room_id = release['RoomId']
            release_date = self.get_datetime(release['Date'])
            self.spoilers.append({'type': 'room', 'date': release_date, 'id': room_id})
        for release in self.user_data['pEconomyModel']['WeaponReleaseDates']:
            weapon_id = release['WeaponId']
            release_date = self.get_datetime(release['Date'])
            if weapon_id in self.weapons:
                self.weapons[weapon_id]['release_date'] = release_date
                self.spoilers.append({'type': 'weapon', 'date': release_date, 'id': weapon_id})
        for release in self.user_data['BasicLiveEventArray']:
            gacha_troop = release['GachaTroop']
            gacha_troops = release.get('GachaTroops', [])
            result = {'start': datetime.datetime.utcfromtimestamp(release['StartDate']).date(),
                      'end': datetime.datetime.utcfromtimestamp(release['EndDate']).date(),
                      'type': EVENT_TYPES.get(release['Type'], release['Type']),
                      'names': release.get('Name'),
                      'gacha': gacha_troop,
                      'troops': gacha_troops,
                      'kingdom_id': release.get('Kingdom')}
            if gacha_troop and gacha_troop in self.troops:
                self.troops[gacha_troop]['event'] = True
            self.events.append(result)

        week_long_events = [e for e in self.events
                            if e['end'] - e['start'] == datetime.timedelta(days=7)
                            and e['kingdom_id']]
        non_craftable_weapon_ids = [
            1102, 1114, 1070, 1073, 1119, 1118, 1108, 1109, 1203, 1092, 1067, 1094, 1179, 1178, 1069, 1127, 1096, 1134,
            1097, 1103, 1115, 1123, 1120, 1071, 1095, 1072, 1107, 1100, 1106, 1213, 1121, 1093, 1122, 1295, 1250, 1317,
            1294, 1239, 1223, 1222, 1272, 1252, 1287, 1275, 1251, 1238, 1224, 1296, 1273, 1274, 1286, 1225
        ]
        for event in week_long_events:
            kingdom_weapons = [w['id'] for w in self.weapons.values()
                               if 'kingdom' in w and w['kingdom']['id'] == event['kingdom_id']
                               and w['id'] not in non_craftable_weapon_ids
                               and w.get('release_date', datetime.datetime.min).date() < event['end']]
            self.soulforge_weapons.append({
                'start': event['start'],
                'end': event['end'],
                'weapon_ids': kingdom_weapons,
            })

        self.events.sort(key=operator.itemgetter('start'))
        self.spoilers.sort(key=operator.itemgetter('date'))

    def enrich_kingdoms(self):
        for kingdom_id, kingdom_data in self.user_data['pEconomyModel']['KingdomLevelData'].items():
            self.kingdoms[int(kingdom_id)]['primary_color'] = COLORS[kingdom_data['Color']]
            self.kingdoms[int(kingdom_id)]['primary_stat'] = kingdom_data['Stat']

        for kingdom_id, pet_id in self.user_data['pEconomyModel']['FactionRenownRewardPetIds'].items():
            self.kingdoms[int(kingdom_id)]['pet'] = self.pets[pet_id]

        factions = [(k_id, kingdom) for k_id, kingdom in self.kingdoms.items() if
                    kingdom['underworld'] and kingdom['troop_ids']]
        for faction_id, faction_data in factions:
            kingdom_id = faction_data['linked_kingdom_id']
            faction_weapons = [w['id'] for w in self.weapons.values()
                               if w['kingdom']['id'] == kingdom_id
                               and w['requirement'] == 1000
                               and sorted(w['colors']) == sorted(faction_data['colors'])
                               and w['rarity'] == 'Epic'
                               ]
            if faction_weapons:
                weapon_id = faction_weapons[-1]
                self.kingdoms[faction_id]['event_weapon'] = self.weapons[weapon_id]
                self.weapons[weapon_id]['event_faction'] = faction_id

    def populate_soulforge(self):
        tabs = [
            '[SOULFORGE_TAB_LEVEL]',
            '[SOULFORGE_TAB_JEWELS]',
            '[SOULFORGE_TAB_TRAITSTONES]',
            '[SOULFORGE_TAB_TROOPS]',
            '[SOULFORGE_TAB_WEAPONS]',
            '[SOULFORGE_TAB_OTHER]',
        ]

        for recipe in self.soulforge_raw_data.get('pRecipeArray', []):
            if recipe['Tab'] in (3, 4):
                recipe_id = recipe['Target']['Data']
                if recipe_id < 1000 or recipe_id in SOULFORGE_ALWAYS_AVAILABLE:
                    continue
                if not recipe['Name']:
                    recipe['Name'] = self.troops[recipe_id]['name']
                    recipe['rarity'] = self.troops[recipe_id]['rarity']
                category = tabs[recipe['Tab']]
                self.soulforge.setdefault(category, []).append({
                    'name': recipe['Name'],
                    'id': recipe_id,
                    'costs': recipe['Source'],
                    'start': recipe['StartDate'],
                    'end': recipe['EndDate'],
                    'rarity': recipe.get('rarity', 'Z'),
                })

    def populate_traitstones(self):
        for traits in self.user_data['pTraitsTable']:
            runes = self.extract_runes(traits['Runes'])
            for rune in runes:
                if rune['name'] in self.traitstones:
                    self.traitstones[rune['name']]['total_amount'] += rune['amount']
                else:
                    self.traitstones[rune['name']] = {
                        'id': rune['id'],
                        'name': rune['name'],
                        'troop_ids': [],
                        'class_ids': [],
                        'kingdom_ids': [],
                        'total_amount': rune['amount'],
                    }
                if 'ClassCode' in traits:
                    class_id = [_class for _class in self.classes.values()
                                if _class['code'] == traits['ClassCode']][0]['id']
                    self.classes[class_id]['traitstones'] = runes
                    self.traitstones[rune['name']]['class_ids'].append(class_id)
                elif traits['Troop'] in self.troops:
                    self.troops[traits['Troop']]['traitstones'] = runes
                    self.traitstones[rune['name']]['troop_ids'].append(traits['Troop'])
        for kingdom_id, runes in self.user_data['pEconomyModel']['Explore_RunePerKingdom'].items():
            for rune_id in runes:
                rune_name = self.get_rune_name_from_id(rune_id)
                self.traitstones[rune_name]['kingdom_ids'].append(kingdom_id)

    def extract_runes(self, runes):
        result = {}
        for trait in runes:
            for rune in trait:
                rune_id = rune['Id']
                if rune_id in result:
                    result[rune_id]['amount'] += rune['Required']
                else:
                    result[rune_id] = {
                        'id': rune['Id'],
                        'name': self.get_rune_name_from_id(rune['Id']),
                        'amount': rune['Required'],
                    }
        return list(result.values())

    @staticmethod
    def get_rune_name_from_id(rune_id):
        return f'[RUNE{rune_id:02d}_NAME]'

    def populate_hero_levels(self):
        for bonus in self.user_data['pEconomyModel']['HeroLevelUpStats']:
            level_bonus = {
                'level': bonus['Level'],
                'bonus': f'[{bonus["Stat"].upper()}]',
            }
            self.levels.append(level_bonus)

    def populate_max_power_levels(self):
        pattern = re.compile(r'KingdomTask(?P<level>[0-9]+)-.+')
        for kingdom in self.kingdoms.values():
            max_kingdom_level = 0
            for task in self.user_data['pTasksData']['Kingdom']:
                match = pattern.match(task['Id'])
                if not match:
                    print(f'Match is broken for kingdom {kingdom}')
                level = match.groups()[0]
                if not self.kingdom_satisfies_task(kingdom, task):
                    break
                max_kingdom_level = int(level)
            self.kingdoms[kingdom['id']]['max_power_level'] = max_kingdom_level

    def kingdom_satisfies_task(self, kingdom, task):
        if task['Task'] in ('IncreaseKingdomLevel', 'CompleteQuestline', 'Complete{x}ChallengesIn{y}'):
            return True
        if task['Task'] == 'Own{x}Troops':
            troops = [self.troops[id_] for id_ in kingdom['troop_ids']]
            troops = [t for t in troops if 'release_date' not in t or t['release_date'] <= datetime.datetime.now()]
            return len(troops) >= task['XValue']
        if task['Task'] == 'Own{x}Weapons':
            weapons = [self.weapons[id_] for id_ in kingdom['weapon_ids']]
            weapons = [w for w in weapons if 'release_date' not in w or w['release_date'] <= datetime.datetime.now()]
            return len(weapons) >= task['XValue']
        if task['Task'] == 'Own{x}Classes':
            classes = [c for c in self.classes.values() if c['kingdom_id'] == kingdom['id']]
            classes = [c for c in classes if 'release_date' not in c or c['release_date'] <= datetime.datetime.now()]
            return len(classes) >= task['XValue']
        if task['Task'] == 'Own{x}Pets':
            pets = [p for p in self.pets.values() if p['kingdom_id'] == kingdom['id']]
            pets = [p for p in pets if 'release_date' not in p or p['release_date'] <= datetime.datetime.now()]
            return len(pets) >= task['XValue']
        if task['Task'] == 'Earn{x}Renown':
            return kingdom['linked_kingdom_id'] and not kingdom['underworld']
        return False

    def populate_adventure_board(self):
        for board in self.user_data['pUser']['AdventureData']:
            name = board['Name']
            rewards = self._transform_adventure_reward(board['Battles'])
            rarity = f'[RARITY_{board["Rarity"]}]'
            self.adventure_board.append({
                'name': name,
                'rewards': rewards,
                'rarity': rarity,
                'raw_rarity': int(board['Rarity']),
            })

    @staticmethod
    def _transform_adventure_reward(battles):
        result = {}
        for battle in battles:
            for reward in battle['Rewards']:
                reward_type = f'[{reward["Type"].upper()}]'
                amount = reward['Amount']
                data = reward['Data']
                if reward_type == '[GEM]':
                    reward_type = '[GEMS]'
                elif reward_type == '[SOUL]':
                    reward_type = '[SOULS]'
                elif reward_type == '[DEED]':
                    reward_type = f'[DEED{data:02d}]'
                elif reward_type == '[RUNE]':
                    reward_type = f'[RUNE{data:02d}_NAME]'
                elif reward_type == '[KEY]':
                    reward_type = f'[KEYTYPE_{data}_TITLE]'
                result.setdefault(reward_type, 0)
                result[reward_type] += amount
        return result
