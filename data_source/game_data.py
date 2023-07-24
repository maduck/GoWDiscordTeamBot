import datetime
import math
import operator
import re

from configurations import CONFIG
from data_source import Pets
from event_helpers import extract_currencies, extract_lore, extract_name, get_first_battles, roles_translation, \
    transform_battle
from game_assets import GameAssets
from game_constants import COLORS, COST_TYPES, EVENT_TYPES, GEM_TUTORIAL_IDS, OrbType, RewardTypes, \
    SOULFORGE_ALWAYS_AVAILABLE
from game_constants.soulforge import NON_CRAFTABLE_WEAPON_IDS
from util import U, convert_color_array

FIRST_ARCANE_TRAITSTONE_INDEX = 18

NO_TRAIT = {'code': '', 'name': '[TRAIT_NONE]', 'description': '[TRAIT_NONE_DESC]'}


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

        self.troops = {'`?`': {'name': '`?`', 'color_code': 'questionmark'}}
        self.troop_types = set()
        self.spells = {}
        self.effects = set()
        self.positive_effects = {'BARRIER', 'ENCHANTED', 'ENRAGED', 'SUBMERGED', 'BLESSED', 'MIRROR'}
        self.weapons = {}
        self.classes = {}
        self.banners = {}
        self.traits = {}
        self.kingdoms = {
            '`?`': {'name': '[REQUIREMENTS_NOT_MET]', 'underworld': False, 'filename': None, 'id': '`?`',
                    'location': None, 'reference_name': '`?`'}}
        self.pet_effects = ()
        self.pets: Pets = None
        self.talent_trees = {}
        self.spoilers = []
        self.events = []
        self.soulforge_weapons = []
        self.campaign_tasks = {}
        self.campaign_data = {}
        self.campaign_skip_costs = {}
        self.campaign_rerolls = {}
        self.campaign_week = None
        self.artifact_id = None
        self.campaign_name = ''
        self.soulforge = {}
        self.summons = {}
        self.soulforge_raw_data = {}
        self.traitstones = {}
        self.levels = []
        self.adventure_board = []
        self.drop_chances = {}
        self.event_chest_drops = {}
        self.event_kingdoms = []
        self.event_raw_data = {}
        self.weekly_event = {}
        self.gem_events = {}
        self.store_raw_data = {}
        self.store_data = {}
        self.hoard_potions = {}
        self.orbs = {}

    def read_json_data(self):
        self.data = GameAssets.load('World.json')
        self.user_data = GameAssets.load('User.json')
        if GameAssets.exists('Campaign.json'):
            self.campaign_data = GameAssets.load('Campaign.json')
        if GameAssets.exists('Soulforge.json'):
            self.soulforge_raw_data = GameAssets.load('Soulforge.json')
        if GameAssets.exists('Event.json'):
            self.event_raw_data = GameAssets.load('Event.json')
        if GameAssets.exists('Store.json'):
            self.store_raw_data = GameAssets.load('Store.json')

    def populate_world_data(self):
        self.read_json_data()

        self.populate_spells()
        self.populate_traits()
        self.populate_troops()
        self.pets = Pets(self.data['Pets'], self.user_data, self.troops)
        self.populate_kingdoms()
        self.populate_weapons()
        self.populate_talents()
        self.populate_classes()
        self.populate_release_dates()
        self.enrich_kingdoms()
        self.add_troops_to_kingdoms_by_filename()
        self.populate_campaign_tasks()
        self.populate_soulforge()
        self.populate_traitstones()
        self.populate_hero_levels()
        self.populate_max_power_levels()
        self.populate_adventure_board()
        self.populate_drop_chances()
        self.populate_event_key_drops()
        self.populate_event_kingdoms()
        self.populate_store_data()
        self.populate_weekly_event_details()
        self.populate_gem_events()
        self.populate_hoard_potions()
        self.populate_orbs()

    def populate_classes(self):
        for _class in self.data['HeroClasses']:
            if _class['KingdomId'] not in self.kingdoms:
                _class['KingdomId'] = '`?`'
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

    def populate_weapons(self):
        for weapon in self.data['Weapons']:
            colors = convert_color_array(weapon)
            self.weapons[weapon['Id']] = {
                'id': weapon['Id'],
                'name': f'[SPELL{weapon["SpellId"]}_NAME]',
                'description': f'[SPELL{weapon["SpellId"]}_DESC]',
                'colors': colors,
                'rarity': weapon['WeaponRarity'],
                'type': weapon['Type'],
                'roles': weapon['TroopRoleArray'],
                'spell_id': weapon['SpellId'],
                'kingdom': self.kingdoms[weapon['KingdomId']],
                'kingdom_id': weapon['KingdomId'],
                'requirement': weapon.get('MasteryRequirement', 0),
                'armor_increase': weapon['ArmorIncrease'],
                'attack_increase': weapon['AttackIncrease'],
                'health_increase': weapon['HealthIncrease'],
                'magic_increase': weapon['SpellPowerIncrease'],
                'affixes': [self.spells.get(spell) for spell in weapon['Affixes'] if spell in self.spells],
            }
            self.kingdoms[weapon['KingdomId']]['weapon_ids'].append(weapon['Id'])

    def populate_kingdoms(self):
        for kingdom in self.data['Kingdoms']:
            self.pets.fill_untranslated_kingdom_name(kingdom['Id'], kingdom['ReferenceName'])
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
            for troop_id in kingdom_troops:
                if troop_id in self.troops:
                    self.troops[troop_id]['kingdom_id'] = kingdom['Id']
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
                'reference_name': kingdom['ReferenceName'],
                'coordinates': (kingdom['XPos'], kingdom['YPos']),
                'links': set(kingdom['Links']),
            }
            if 'SisterKingdomId' in kingdom:
                self.kingdoms[kingdom['SisterKingdomId']]['linked_kingdom_id'] = kingdom['Id']
            for troop_id in kingdom_troops:
                if troop_id in self.troops:
                    self.troops[troop_id]['kingdom'] = self.kingdoms[kingdom['Id']]

    @staticmethod
    def infer_kingdom_location(kingdom):
        if 'WARBAND' in kingdom['ReferenceName']:
            return 'warband'
        return 'underworld' if kingdom.get('MapIndex', 0) == 1 else 'krystara'

    def populate_troops(self):
        for troop in self.data['Troops']:
            colors = convert_color_array(troop)
            self.troops[troop['Id']] = {
                'id': troop['Id'],
                'name': troop['Name'],
                'reference_name': troop['ReferenceName'],
                'colors': sorted(colors),
                'description': troop['Description'],
                'spell_id': troop['SpellId'],
                'has_shiny': troop.get('HasShiny', False),
                'shiny_spell_id': troop.get('ShinySpellId'),
                'traits': [self.traits.get(trait, NO_TRAIT) for trait in
                           troop['Traits']],
                'rarity': troop['TroopRarity'],
                'types': [troop['TroopType']],
                'roles': troop['TroopRoleArray'],
                'kingdom': {'name': '', 'reference_name': ''},
                'filename': troop['FileBase'],
                'armor': sum(troop['ArmorIncrease']),
                'health': sum(troop['HealthIncrease']),
                'magic': sum(troop['SpellPowerIncrease']),
                'attack': sum(troop['AttackIncrease']),
            }
            if 'TroopType2' in troop:
                self.troops[troop['Id']]['types'].append(troop['TroopType2'])
            for type_ in self.troops[troop['Id']]['types']:
                self.troop_types.add(type_)

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
                if step.get('Type', '').lower().startswith('cause'):
                    effect_code = step['Type'].upper().replace('CAUSE', '')
                    self.effects.add(effect_code.upper())
                if 'Type' in step and 'SpellPowerMultiplier' in step:
                    amount = step.get('Amount', 0)
                    multiplier = step.get('SpellPowerMultiplier', 1)
                    if last_type != step['Type']:
                        spell_effects.append([multiplier, amount])
                        last_type = step['Type']
                if step['Type'].startswith('Count') \
                        and not step['Type'].endswith('Max') \
                        and not step['Type'].endswith('Min'):
                    boost = step.get('Amount', 1)
            self.spells[spell['Id']] = {
                'id': spell['Id'],
                'name': spell['Name'],
                'description': spell['Description'],
                'cost': spell.get('Cost', '[N/A]'),
                'effects': spell_effects,
                'boost': boost,
            }

        self.effects -= {'SPECIFICSTATUSEFFECTCONDITIONAL', 'ALLPOSITIVESTATUSEFFECTS', 'ALLNEGATIVESTATUSEFFECTS'}

    def get_current_event_kingdom_id(self):
        if 'CurrentEventKingdomId' in self.user_data['pEconomyModel']:
            return self.user_data['pEconomyModel']['CurrentEventKingdomId']
        today = datetime.date.today()
        weekly_events = [e for e in self.events
                         if e['end'] - e['start'] == datetime.timedelta(days=7)
                         and e['start'] <= today <= e['end']
                         and e['start'].weekday() == 0
                         and e['kingdom_id']
                         and e['type'] == '[WEEKLY_EVENT]']
        return int(weekly_events[0]['kingdom_id']) if weekly_events else 3000

    def get_current_campaign_week(self):
        if self.campaign_week:
            return self.campaign_week
        release_dates = self.user_data['pEconomyModel']['ArtifactReleaseDates']
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=CONFIG.get('data_shift_hours'))
        for release in release_dates:
            artifact_release = datetime.datetime.strptime(release['Date'], '%m/%d/%Y %H:%M:%S %p %Z')
            release_age = now - artifact_release
            if datetime.timedelta(days=0) <= release_age <= datetime.timedelta(days=10 * 7):
                week_no = math.ceil(release_age / datetime.timedelta(days=7))
                self.artifact_id = release['ArtifactId']
                self.campaign_week = week_no
                return week_no
        current_artifact_id = self.user_data['pEconomyModel']['LowestUnpurchasableArtifactId']
        event_kingdom_id = self.get_current_event_kingdom_id()
        week = 1
        for artifact in self.data['Artifacts']:
            if artifact['Id'] != current_artifact_id:
                continue
            for week, level in enumerate(artifact['Levels']):
                if level['KingdomId'] == event_kingdom_id:
                    break
        self.artifact_id = current_artifact_id
        self.campaign_week = week
        return week

    def populate_campaign_tasks(self):
        event_kingdom_id = self.get_current_event_kingdom_id()
        week = self.get_current_campaign_week()
        for artifact in self.data['Artifacts']:
            if artifact['Id'] == self.artifact_id:
                self.campaign_name = artifact['Name']

        tasks = self.user_data['pTasksData']['CampaignTasks'][str(event_kingdom_id)]
        rerolls = self.user_data['pTasksData']['CampaignRerollTasks']

        level_nums = {
            'Gold': 2,
            'Silver': 4,
            'Bronze': 10,
        }

        for level in ('Gold', 'Silver', 'Bronze'):
            task_list = [self.transform_campaign_task(task, week) for task in tasks[level]]
            task_list = sorted(task_list, key=operator.itemgetter('order'))
            task_list = task_list[-level_nums[level]:]
            self.campaign_tasks[level.lower()] = task_list
            reroll_list = [self.transform_campaign_task(task, week) for task in rerolls[f'Campaign{level}']]
            self.campaign_rerolls[level.lower()] = reroll_list
        self.campaign_tasks['kingdom'] = self.kingdoms[event_kingdom_id]
        self.populate_campaign_skip_costs()

    def populate_campaign_skip_costs(self):
        level_names = {
            'CampaignBronze': '[MEDAL_LEVEL_0]',
            'CampaignSilver': '[MEDAL_LEVEL_1]',
            'CampaignGold': '[MEDAL_LEVEL_2]',
        }
        for level, cost in self.user_data['pEconomyModel']['CampaignTaskSkipCost'].items():
            level_name = level_names[level]
            self.campaign_skip_costs[level_name] = cost

    def transform_campaign_task(self, task, week):
        extra_data = {}
        task_order = 0
        kingdom_id = 0
        if 'Reroll' not in task['Id']:
            m = re.match(r'Campaign_(?P<kingdom_id>\d+)_(?P<level>.+)_(?P<order>\d+)', task['Id'])
            task_id = m.groupdict()
            task_order = 1
            kingdom_id = int(task_id['kingdom_id'])
            level = task_id['level']
        else:
            level = task['Id'].split('_')[2]

        for i, t in enumerate(self.campaign_data.get(f'Campaign{level}', [])):
            if t and t['Id'] == task['Id']:
                extra_data = t
                task_order = i

        if task['TaskTitle'].endswith('CRYSTALS]') or (
                task['TaskTitle'] == '[TASK_COLOR_SLAYER]' and 'Reroll' in task['Id']) or (
                task['TaskTitle'] == '[TASK_GRAVE_KEEPER]'):
            extra_data['Value1'] = task['YValue']
        elif task['TaskTitle'] == '[TASK_DEEP_DELVER]':
            extra_data['Value1'] = 10 * (week + 1)
        elif task['TaskTitle'] == '[TASK_INTREPID_EXPLORER]':
            extra_data['Value1'] = week
        elif task['TaskTitle'] == '[TASK_FORGOTTEN_EXPLORER]' and 'Reroll' in task['Id']:
            extra_data['Value1'] = '`Current Campaign Week`'

        return {
            'reward': task['Rewards'][0]['Amount'],
            'condition': task.get('Condition'),
            'order': task_order,
            'task': task['Task'],
            'name': task['TaskName'],
            'title': task['TaskTitle'],
            'tags': task.get('Tag', '').split(','),
            'x': task.get('XValue'),
            'y': task.get('YValue'),
            'value0': U(extra_data.get('Value0', '`?`')),
            'value1': U(extra_data.get('Value1', '`?`')),
            'c': U(task.get('CValue')),
            'd': U(task.get('DValue')),
            'kingdom_id': kingdom_id,
            'orig': task,
        }

    @staticmethod
    def get_datetime(val):
        date_format = '%m/%d/%Y %I:%M:%S %p %Z'
        return datetime.datetime.strptime(val, date_format).replace(tzinfo=datetime.timezone.utc)

    def populate_release_dates(self):
        self.populate_troop_release_dates()
        self.populate_pet_release_dates()
        self.populate_kingdom_release_dates()
        self.populate_class_release_dates()
        self.populate_room_release_dates()
        self.populate_weapon_release_dates()
        self.populate_event_release_dates()
        self.populate_weekly_event_dates()

        self.events.sort(key=operator.itemgetter('start'))
        self.spoilers.sort(key=operator.itemgetter('date'))

    def populate_weekly_event_dates(self):
        week_long_events = [e for e in self.events
                            if e['end'] - e['start'] == datetime.timedelta(days=7)
                            and e['kingdom_id']]
        for event in week_long_events:
            kingdom_weapons = [w['id'] for w in self.weapons.values()
                               if 'kingdom' in w and w['kingdom']['id'] == event['kingdom_id']
                               and w['id'] not in NON_CRAFTABLE_WEAPON_IDS
                               and w.get('release_date', datetime.datetime.min).date() < event['end']]
            self.soulforge_weapons.append({
                'start': event['start'],
                'end': event['end'],
                'weapon_ids': kingdom_weapons,
            })

    def populate_event_release_dates(self):
        for release in self.user_data['BasicLiveEventArray']:
            gacha_troop = release['GachaTroop']
            gacha_troops = release.get('GachaTroops', [])
            result = {'id': release['Id'],
                      'start': datetime.datetime.utcfromtimestamp(release['StartDate']).date(),
                      'start_time': datetime.datetime.utcfromtimestamp(release['StartDate']),
                      'end': datetime.datetime.utcfromtimestamp(release['EndDate']).date(),
                      'end_time': datetime.datetime.utcfromtimestamp(release['EndDate']),
                      'type': EVENT_TYPES.get(release['Type'], release['Type']),
                      'names': release.get('Name'),
                      'gacha': gacha_troop,
                      'troops': gacha_troops,
                      'kingdom_id': release.get('Kingdom'),
                      'artifact_id': release.get('ArtifactId'),
                      }
            if gacha_troop and gacha_troop in self.troops:
                self.troops[gacha_troop]['event'] = True
            self.events.append(result)

    def populate_weapon_release_dates(self):
        for release in self.user_data['pEconomyModel']['WeaponReleaseDates']:
            weapon_id = release['WeaponId']
            release_date = self.get_datetime(release['Date'])
            if weapon_id in self.weapons:
                self.weapons[weapon_id]['release_date'] = release_date
                self.spoilers.append({'type': 'weapon', 'date': release_date, 'id': weapon_id})

    def populate_room_release_dates(self):
        for release in self.user_data['pEconomyModel']['RoomReleaseDates']:
            room_id = release['RoomId']
            release_date = self.get_datetime(release['Date'])
            self.spoilers.append({'type': 'room', 'date': release_date, 'id': room_id})

    def populate_class_release_dates(self):
        for release in self.user_data['pEconomyModel']['HeroClassReleaseDates']:
            class_code = release['ClassCode']
            release_date = self.get_datetime(release['Date'])
            if classes := [
                c['id'] for c in self.classes.values() if c['code'] == class_code
            ]:
                class_id = classes[0]
                self.classes[class_id]['release_date'] = release_date
                self.spoilers.append({'type': 'classe', 'date': release_date, 'id': class_id})

    def populate_kingdom_release_dates(self):
        for release in self.user_data['pEconomyModel']['KingdomReleaseDates']:
            kingdom_id = release['KingdomId']
            release_date = self.get_datetime(release['Date'])
            if kingdom_id in self.kingdoms:
                self.kingdoms[kingdom_id]['release_date'] = release_date
                self.spoilers.append({'type': 'kingdom', 'date': release_date, 'id': kingdom_id})

    def populate_pet_release_dates(self):
        for release in self.user_data['pEconomyModel']['PetReleaseDates']:
            pet_id = release['PetId']
            release_date = self.get_datetime(release['Date'])
            if pet_id in self.pets:
                self.pets[pet_id].set_release_date(release_date)
                self.spoilers.append({'type': 'pet', 'date': release_date, 'id': pet_id})

    def populate_troop_release_dates(self):
        release: dict
        for release in self.user_data['pEconomyModel']['TroopReleaseDates']:
            troop_id = release['TroopId']
            release_date = self.get_datetime(release['Date'])
            if troop_id in self.troops:
                self.troops[troop_id]['release_date'] = release_date
                self.spoilers.append({'type': 'troop', 'date': release_date, 'id': troop_id})
                if self.troops[troop_id]['rarity'] == 'Mythic' and 'Id' in self.troops[troop_id]['kingdom']:
                    self.events.append(
                        {'id': 0,
                         'start': release_date.date(),
                         'end': release_date.date() + datetime.timedelta(days=7),
                         'type': '[RARITY_5]',
                         'names': self.troops[troop_id]['name'],
                         'gacha': troop_id,
                         'kingdom_id': self.troops[troop_id]['kingdom']['Id']}
                    )

    def enrich_kingdoms(self):
        for kingdom_id, kingdom_data in self.user_data['pEconomyModel']['KingdomLevelData'].items():
            self.kingdoms[int(kingdom_id)]['primary_color'] = COLORS[kingdom_data['Color']]
            self.kingdoms[int(kingdom_id)]['primary_stat'] = kingdom_data['Stat']

        for kingdom_id, pet_id in self.user_data['pEconomyModel']['FactionRenownRewardPetIds'].items():
            if pet_id in self.pets:
                self.kingdoms[int(kingdom_id)]['pet'] = self.pets[pet_id]

        factions = [(k_id, kingdom) for k_id, kingdom in self.kingdoms.items() if
                    kingdom['underworld'] and kingdom['troop_ids']]

        faction_weapon_overrides = {
            3053: 1274,
            3054: 1391,
            3069: 1272,
        }
        for faction_id, faction_data in factions:
            kingdom_id = faction_data['linked_kingdom_id']
            if faction_weapons := [
                w['id']
                for w in self.weapons.values()
                if w['kingdom']['id'] == kingdom_id
                   and w['requirement'] == 1000
                   and sorted(w['colors']) == sorted(faction_data['colors'])
                   and w['rarity'] == 'Epic'
            ]:
                weapon_id = faction_weapons[-1]
                weapon_id = faction_weapon_overrides.get(faction_id, weapon_id)
                self.kingdoms[faction_id]['event_weapon'] = self.weapons[weapon_id]
                self.weapons[weapon_id]['event_faction'] = faction_id

    def add_troops_to_kingdoms_by_filename(self):
        pattern = re.compile(r'.+_(?P<filebase>K\d+).*')
        for troop_id, troop in self.troops.items():
            if troop_id == '`?`':
                continue
            kingdom = troop['kingdom']
            if kingdom.get('name') or kingdom.get('reference_name'):
                continue
            match = pattern.match(troop['filename'])
            if not match:
                continue
            kingdom_filename = match["filebase"]
            # Skip Apocalypse (3034) and HoG (3042),
            # because they share filename with
            # Sin of Maraj and Guardians resp. and are
            # unlikely to get new troops
            skip_kingdoms = [3034, 3042]
            if troop_kingdom := next(
                    (
                            k
                            for k in self.kingdoms.values()
                            if k['filename'] == kingdom_filename
                               and k['id'] not in skip_kingdoms
                    ),
                    None,
            ):
                troop['kingdom'] = troop_kingdom
                troop_kingdom['troop_ids'].append(troop_id)

                if troop_kingdom['underworld']:
                    krystara_kingdom_id = self.kingdoms[troop_kingdom['id']]['linked_kingdom_id']
                    self.kingdoms[krystara_kingdom_id]['troop_ids'].append(troop_id)

    def populate_soulforge(self):
        tabs = [
            '[SOULFORGE_TAB_LEVEL]',
            '[SOULFORGE_TAB_JEWELS]',
            '[SOULFORGE_TAB_TRAITSTONES]',
            '[SOULFORGE_TAB_TROOPS]',
            '[SOULFORGE_TAB_WEAPONS]',
            '[SOULFORGE_TAB_OTHER]',
        ]

        recipes = [r for r in self.soulforge_raw_data.get('pRecipeArray', []) if r['Tab'] in (3, 4)]
        for recipe in recipes:
            recipe_id = recipe['Target']['Data']
            if recipe_id < 1000 or recipe_id in SOULFORGE_ALWAYS_AVAILABLE:
                continue
            if not recipe['Name']:
                recipe['Name'] = self.troops[recipe_id]['name']
                recipe['rarity'] = self.troops[recipe_id]['rarity']
            if 'rarity' not in recipe:
                if recipe_id in self.weapons:
                    recipe['rarity'] = self.weapons[recipe_id]['rarity']
                elif recipe_id in self.troops:
                    recipe['rarity'] = self.troops[recipe_id]['rarity']
            category = tabs[recipe['Tab']]
            self.soulforge.setdefault(category, []).append({
                'name': recipe['Name'],
                'id': recipe_id,
                'costs': recipe['Source'],
                'start': recipe['StartDate'],
                'end': recipe['EndDate'],
                'rarity': recipe['rarity'],
            })
        for colour, troops in enumerate(self.soulforge_raw_data.get('pSummonTroopArray', [])):
            stone_name = f'[RECIPE_SUMMONS_{colour}]'
            self.summons[stone_name] = [{'troop_id': troop['nTroopId'], 'count': troop['nQuantity']}
                                        for troop in troops]

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
                        'kingdom_ids': set(),
                        'total_amount': rune['amount'],
                    }
                if 'ClassCode' in traits:
                    my_class = [_class for _class in self.classes.values()
                                if _class['code'] == traits['ClassCode']]
                    if not my_class:
                        continue
                    class_id = my_class[0]['id']
                    self.classes[class_id]['traitstones'] = runes
                    self.traitstones[rune['name']]['class_ids'].append(class_id)
                elif traits['Troop'] in self.troops:
                    self.troops[traits['Troop']]['traitstones'] = runes
                    self.traitstones[rune['name']]['troop_ids'].append(traits['Troop'])
        for kingdom_id, runes in self.user_data['pEconomyModel']['Explore_RunePerKingdom'].items():
            for rune_id in runes:
                rune_name = self.get_rune_name_from_id(rune_id)
                self.traitstones[rune_name]['kingdom_ids'].add(kingdom_id)
        for kingdom_id, runes in self.user_data['pEconomyModel']['Rune_AfterBattleKingdomData'].items():
            if kingdom_id == '1000':
                continue
            for rune_id in runes:
                rune_name = self.get_rune_name_from_id(rune_id)
                self.traitstones[rune_name]['kingdom_ids'].add(kingdom_id)

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
        pattern = re.compile(r'KingdomTask(?P<level>\d+)-.+')
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
        valid_ids = [kingdom['id']]
        if kingdom['location'] == 'krystara' and kingdom['linked_kingdom_id']:
            valid_ids.append(kingdom['linked_kingdom_id'])

        def has_enough(items):
            items = [i for i in items.values() if i.get('kingdom_id') in valid_ids]
            now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            items = [i for i in items if 'release_date' not in i or i['release_date'] <= now]
            return len(items) >= task['XValue']

        def has_enough_new_style(items):
            items = [i.data for i in items.items.values() if i.data.get('kingdom_id') in valid_ids]
            now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            items = [i for i in items if 'release_date' not in i or i['release_date'] <= now]
            return len(items) >= task['XValue']

        if task['Task'] in ('IncreaseKingdomLevel', 'CompleteQuestline', 'Complete{x}ChallengesIn{y}'):
            return True
        if task['Task'] == 'Own{x}Troops':
            return has_enough(self.troops)
        if task['Task'] == 'Own{x}Weapons':
            return has_enough(self.weapons)
        if task['Task'] == 'Own{x}Classes':
            return has_enough(self.classes)
        if task['Task'] == 'Own{x}Pets':
            return has_enough_new_style(self.pets)
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

    def _transform_adventure_reward(self, battles):
        result = {}
        for battle in battles:
            for reward in battle['Rewards']:
                amount = reward['Amount']
                reward_type = self.translate_reward_type(reward)
                result.setdefault(reward_type, 0)
                result[reward_type] += amount
        return result

    def translate_reward_type(self, reward):
        reward_type = f'[{reward["Type"].upper()}]'
        data = reward['Data']
        if reward_type == '[TROOP]':
            data = self.troops.get(data)
        reward_translation = {
            '[GEM]': '[GEMS]',
            '[SOUL]': '[SOULS]',
            '[DEED]': '[DEED{data:02d}]',
            '[RUNE]': '[RUNE{data:02d}_NAME]',
            '[PETFOOD]': '[PETFOOD{data:02d}_NAME]',
            '[KEY]': '[KEYTYPE_{data}_TITLE]',
            '[VAULTKEY]': '[LIVEEVENTENERGY3]',
            '[ORB]': '[REWARD_HELP_HEADING_ORB_{data}]',
            '[DIAMOND]': '[DIAMONDS_GAINED]',
            '[MEDAL]': '[WONDER_{data}_NAME]',
            '[CHATTITLE]': '[TITLE]',
            '[CHATPORTRAIT]': '[PORTRAIT]',
            '[TROOP]': '{data[name]}',
            '[CHAOSSHARD]': '[N_CHAOS_SHARD]',
            '[DEEDBOOK]': '[N_DEEDBOOKS{data:02d}]',
        }
        return reward_translation.get(reward_type, reward_type).format(data=data)

    def populate_drop_chances(self):
        for chest_id, chest in self.user_data['ChestInfo'].items():
            if len(chest_id) != 1:
                continue
            drop_chances = chest['DropChances']
            chest_type = f'[KEYTYPE_{chest_id}_TITLE]'
            for drop in drop_chances.values():
                multipliers = [1 for _ in range(len(drop['RarityChance']))]
                multipliers = drop.get('Multiples', multipliers)

                drop_type = f'[{drop["Type"].upper()}]'
                title = drop.get('Title', drop_type)
                if title == '[RUNE]':
                    title = '[SOULFORGE_TAB_TRAITSTONES]'
                self.drop_chances.setdefault(chest_type, {})
                if title in ('[TROOPS]', '[CHESTS_6_HELP_1]'):
                    self.drop_chances[chest_type].setdefault(title, {})
                    self.drop_chances[chest_type][title] = {
                        f'[RARITY_{i}]': {
                            'chance': chance,
                        } if multiple == 1 else {
                            'chance': chance,
                            'multiplier': multiple,
                        }
                        for i, (multiple, chance) in enumerate(zip(multipliers, drop['RarityChance'])) if chance
                    }
                else:
                    self.drop_chances[chest_type].setdefault('[RESOURCES]', {})
                    self.drop_chances[chest_type]['[RESOURCES]'][title] = {'chance': sum(drop['RarityChance'])}

    def populate_event_key_drops(self):
        self.event_chest_drops = {
            'troop_ids': self.user_data['ChestInfo']['3']['DisplayTroopIds'],
            'kingdom_id': self.user_data['ChestInfo']['3']['KingdomId'],
        }

    def populate_event_kingdoms(self):
        current_event_kingdom = self.get_current_event_kingdom_id()
        campaign_events = [e for e in self.events if e['type'] == '[CAMPAIGN]' and e['start'] <= datetime.date.today()]
        if not campaign_events:
            return
        current_artifact_id = campaign_events[0]['artifact_id']
        self.artifact_id = current_artifact_id
        event_kingdoms = []
        for artifact in self.data['Artifacts']:
            if artifact['Id'] < current_artifact_id:
                continue
            current_campaign_week = self.get_current_campaign_week()
            if artifact['Id'] > current_artifact_id:
                current_campaign_week = 1
            event_kingdoms.extend([level['KingdomId'] for level in artifact['Levels']][current_campaign_week:])
            event_kingdoms.append(0)
        if current_event_kingdom in event_kingdoms:
            index = event_kingdoms.index(current_event_kingdom)
            self.event_kingdoms = event_kingdoms[index + 1:]

    def populate_weekly_event_details(self):

        def extract_restrictions(raw_data):

            restrictions = raw_data.get('PlayerTeamRestrictions', {})
            if EVENT_TYPES[raw_data['Type']] == '[TOWER_OF_DOOM]':
                restrictions = {'ManaColors': [raw_data['Color']]}
            elif EVENT_TYPES[raw_data['Type']] == '[JOURNEY]':
                restrictions = {'ManaColors': [raw_data['Color']], 'TroopTypes': [raw_data['TroopType']]}
            return {
                '[FILTER_MANACOLOR]': restrictions.get('ManaColors'),
                '[KINGDOM]': [self.kingdoms[k]['name'] for k in restrictions.get('KingdomIds', [])],
                '[TROOP_TYPES]': restrictions.get('TroopTypes'),
                '[FILTER_WEAPONTYPE]': restrictions.get('WeaponTypes'),
                '[RARITY]': restrictions.get('TroopRarities'),
                '[FILTER_ROLE]': roles_translation(restrictions.get('Roles', [])),
                '[ROSTER]': restrictions.get('RosterIds'),
            }

        def extract_rewards(raw_data):
            rewards = {}
            points = 0
            for i, stage in enumerate(raw_data.get('RewardStageArray', []), start=1):
                rewards[i] = {
                    'points': stage['Total'],
                    'cumulative': points,
                    'rewards': [],
                }
                points += stage['Total']
                for reward in stage.get('RewardArray', []):
                    rewards[i]['rewards'].append(transform_reward(reward))
            return rewards

        def transform_reward(reward):
            reward_type = self.translate_reward_type(reward)
            return {
                'type': reward_type,
                'data': reward['Data'],
                'amount': reward['Amount'],
            }

        def calculate_minimum_tier():
            score_per_member = math.ceil(
                sum(r['points'] for r in self.weekly_event['rewards'].values()) / 30)
            self.weekly_event['score_per_member'] = score_per_member
            minimum_battles = 0
            entry_no = 0
            for i, entry in enumerate(self.event_raw_data['GlobalLeaderboard']):
                if entry['Score'] >= score_per_member:
                    minimum_battles = entry.get('BattlesWon', 1)
                    entry_no = i
            # here basically everybody in the top 100 is over the required score already,
            # that happens later throughout the week.
            if entry_no == len(self.event_raw_data['GlobalLeaderboard']) - 1:
                all_battles = [e.get('BattlesWon', 0) or 0 for e in self.event_raw_data['GlobalLeaderboard']]
                all_scores = [e.get('Score', 0) for e in self.event_raw_data['GlobalLeaderboard']]
                avg_battles = sum(all_battles) / len(all_battles)
                avg_score = sum(all_scores) / len(all_scores)
                minimum_battles = math.ceil(avg_battles * score_per_member / avg_score)

            if EVENT_TYPES.get(self.weekly_event['type']) == '[RAIDBOSS]':
                """
                formula for damage to score conversion is:
                score = 0.2 battles^2 + 7 battles - 220
                
                inverted:
                battles = 1/2 (-sqrt(20 score + 5625) - 35)
                
                boss starts after 10 fights, with a level 20, and increases by 5 each battle.                
                """
                minimum_battles = (minimum_battles - 20) // 5 + 10

            self.weekly_event['minimum_battles'] = minimum_battles
            tier_battles = [62, 67, 75, 81, 94]
            minimum_tier = 5
            for tier, battles in enumerate(tier_battles):
                if minimum_battles and minimum_battles <= battles:
                    minimum_tier = tier
                    break
            if EVENT_TYPES[self.weekly_event['type']] == '[JOURNEY]':
                minimum_tier = max(minimum_tier, 3)
            self.weekly_event['minimum_tier'] = minimum_tier

        battles = [transform_battle(b) for b in self.event_raw_data.get('BattleArray', [])]

        self.weekly_event = {
            'id': self.event_raw_data['Id'],
            'shop_tiers': [self.store_data[gacha] for gacha in self.event_raw_data.get('GachaItems', [])
                           if gacha in self.store_data],
            'kingdom_id': str(self.event_raw_data.get('Kingdom')),
            'type': self.event_raw_data.get('Type'),
            'name': extract_name(self.event_raw_data),
            'lore': extract_lore(self.event_raw_data),
            'restrictions': extract_restrictions(self.event_raw_data),
            'troop_id': self.event_raw_data.get('GachaTroop'),
            'troop': self.troops[self.event_raw_data.get('GachaTroop', 6000)]['name']
            if self.event_raw_data.get('GachaTroop') else None,
            'color': COLORS[self.event_raw_data.get('Color')] if 'Color' in self.event_raw_data else None,
            'weapon_id': self.event_raw_data.get('EventWeaponId'),
            'token': self.event_raw_data.get('TokenId'),
            'badge': self.event_raw_data.get('BadgeId'),
            'medal': self.event_raw_data.get('MedalId'),
            'currencies': extract_currencies(self.event_raw_data),
            'rewards': extract_rewards(self.event_raw_data),
            'battles': battles,
            'start': datetime.datetime.utcfromtimestamp(self.event_raw_data['StartDate']),
            'end': datetime.datetime.utcfromtimestamp(self.event_raw_data['EndDate']),
            'first_battles': get_first_battles(self.event_raw_data),
        }
        calculate_minimum_tier()

    def populate_gem_events(self):
        for gem_event in self.user_data['pGemEventData']:
            color = COLORS[gem_event['GemType']]
            self.gem_events[gem_event['Id']] = {
                'event_id': gem_event['Id'],
                'gem_id': gem_event['GemType'],
                'gem_type': color,
                'multiplier': gem_event['Multiplier'],
                'tutorial': GEM_TUTORIAL_IDS.get(color, color),
            }

    def populate_store_data(self):
        for entry in self.store_raw_data['ShopData']:
            if not entry['Visible']:
                continue

            rewards = []
            if entry['RewardType'] == RewardTypes.Bundle:
                rewards.extend(self.extract_reward_bundles(entry))

            self.store_data[entry['Code']] = {
                'title': entry['TitleId'],
                'reference': entry['ReferenceName'],
                'cost': entry['Cost'],
                'currency': COST_TYPES[entry['CostType']],
                'tab': entry.get('Tab'),
                'rewards': rewards,
                'visible': entry.get('Visible') == 'True',
            }

    def extract_reward_bundles(self, entry):
        rewards = []
        for reward in entry.get('BundleData', {}):
            if reward['RewardType'] == RewardTypes.Troop and reward['RewardData'] in self.troops:
                rewards.append({
                    'name': self.troops[reward['RewardData']]['name'],
                    'id': reward['RewardData'],
                    'amount': reward['Reward'],
                })
            elif reward['RewardType'] == RewardTypes.Weapon and reward['RewardData'] in self.weapons:
                rewards.append({
                    'name': self.weapons[reward['RewardData']]['name'],
                    'id': reward['RewardData'],
                    'amount': reward['Reward'],
                })
            elif reward['RewardType'] == RewardTypes.LiveEventPoolTroop:
                rewards.append({
                    'id': 0,
                    'name': '[N_EVENT_POOL_TROOPS]',
                    'amount': reward['Reward'],
                })
            elif reward['RewardType'] == RewardTypes.TraitStones \
                    and reward['RewardData'] >= FIRST_ARCANE_TRAITSTONE_INDEX:
                rewards.append({
                    'id': 0,
                    'name': f'[RUNE{reward["RewardData"]:02d}_NAME]',
                    'amount': reward['Reward'],
                })
            elif reward['RewardType'] == RewardTypes.LiveEventPotion:
                rewards.append({
                    'id': 0,
                    'name': f'[LIVEEVENTPOTION{reward["RewardData"]:02d}_NAME]',
                    'amount': reward['Reward'],
                })
        return rewards

    def populate_hoard_potions(self):
        if 'TreasureHoardPotions' not in self.user_data['pFeatures']:
            return
        for potion in self.user_data['pFeatures']['TreasureHoardPotions']:
            potion_data = self.user_data['pFeatures']['TreasureHoardPotionData'][potion['PotionId']]
            traits = [self.traits[t] for t in potion_data.get('Traits', [])]
            self.hoard_potions[potion['PotionId']] = {
                'id': potion['PotionId'],
                'image': f'potion_{potion["PotionId"]:02d}',
                'name': f'[REWARD_HELP_HEADING_LIVEEVENTPOTION_{potion["PotionId"]}]',
                'description': f'[REWARD_HELP_DESC_LIVEEVENTPOTION_1{potion["PotionId"]}]',
                'level': potion['Level'],
                'recurring': potion['Recurring'],
                'reference_name': potion_data['Name'],
                'traits': traits,
                'skills': potion_data.get('SkillBonuses', []),
            }

    def populate_orbs(self):
        chances = [c[0] if c[0] else c[1] for c in zip(
            self.user_data['pEconomyModel']['ChaosOrbChances'],
            self.user_data['pEconomyModel']['MajorChaosOrbChances']
        )]

        orb_groups = [
            f'[ORB_{i:02d}_NAME]' for i in
            (0, 0, 2, 2, 4, 4, 6, 6, 8, 8, 10, 11, 11, 13, 13, 15, 15, 17, 17, 17)
        ]

        for i, orb in enumerate(OrbType):
            self.orbs[orb] = {
                'code': orb.name,
                'emoji': f'Orbs_Orb_{orb.name}_full',
                'name': f'[ORB_{i:02d}_NAME]',
                'data': self.user_data['pEconomyModel']['OrbPowerIncrements'][i],
                'help': f'[REWARD_HELP_DESC_ORB_{i}]',
                'chance': chances[i],
                'group': orb_groups[i],
            }
