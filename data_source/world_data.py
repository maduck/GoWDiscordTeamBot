import json
import operator
import os
import datetime


class WorldData:
    COLORS = ('blue', 'green', 'red', 'yellow', 'purple', 'brown')

    def __init__(self):
        self.EVENT_TYPES = {
            0: '[GUILD_WARS]',
            2: '[INVASION]',
            3: '[VAULT]',
            4: '[BOUNTY]',
            5: '[PETRESCUE]',
            6: '[CLASS_EVENT]',
            7: '[DELVE_EVENT]',
            9: '[HIJACK]',
            10: '[ADVENTURE_BOARD_SPECIAL_EVENT]',
            11: '[CAMPAIGN]',
        }
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
        self.spoilers = []
        self.events = []

    @staticmethod
    def _convert_color_array(data_object):
        return [c.replace('Color', '').lower() for c, v in data_object['ManaColors'].items() if v]

    def read_json_data(self):
        with open('World.json') as f:
            self.data = json.load(f)
        if os.path.exists('User.json'):
            with open('User.json', encoding='utf8') as f:
                self.user_data = json.load(f)

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

    def populate_classes(self):
        for _class in self.data['HeroClasses']:
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
            colors = self._convert_color_array(pet)
            self.pets[pet['Id']] = {
                'id': pet['Id'],
                'name': pet['Name'],
                'kingdom': self.kingdoms[pet['KingdomId']],
                'colors': sorted(colors),
                'effect': self.pet_effects[pet['Effect']],
                'effect_data': pet.get('EffectData'),
                'troop_type': pet.get('EffectTroopType'),
            }

    def populate_weapons(self):
        for weapon in self.data['Weapons']:
            colors = self._convert_color_array(weapon)
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

    def populate_kingdoms(self):
        for kingdom in self.data['Kingdoms']:
            colors = [f'[GEM_{c.upper()}]' for c in self.COLORS]
            colors = zip(colors, kingdom['BannerColors'])
            colors = sorted(colors, key=operator.itemgetter(1), reverse=True)
            self.banners[kingdom['Id']] = {
                'name': kingdom['BannerName'],
                'colors': colors,
                'filename': kingdom['FileBase'],
            }
            kingdom_troops = [troop_id for troop_id in kingdom['TroopIds'] if troop_id != -1]
            kingdom_colors = self._convert_color_array(kingdom)
            self.kingdoms[kingdom['Id']] = {
                'id': kingdom['Id'],
                'name': kingdom['Name'],
                'description': kingdom['Description'],
                'punchline': kingdom['ByLine'],
                'underworld': bool(kingdom.get('MapIndex', 0)),
                'troop_ids': kingdom_troops,
                'troop_type': kingdom['KingdomTroopType'],
                'linked_kingdom_id': kingdom.get('SisterKingdomId'),
                'colors': sorted(kingdom_colors),
            }
            if 'SisterKingdomId' in kingdom:
                self.kingdoms[kingdom['SisterKingdomId']]['linked_kingdom_id'] = kingdom['Id']
            for troop_id in kingdom_troops:
                self.troops[troop_id]['kingdom'] = kingdom

    def populate_troops(self):
        for troop in self.data['Troops']:
            colors = self._convert_color_array(troop)
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
                'filename': troop["FileBase"],
            }
            if 'TroopType2' in troop:
                self.troops[troop['Id']]['types'].append(troop['TroopType2'])

    def populate_traits(self):
        for trait in self.data['Traits']:
            self.traits[trait['Code']] = {'name': trait['Name'], 'description': trait['Description']}

    def populate_spells(self):
        for spell in self.data['Spells']:
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

    def populate_release_dates(self):
        date_format = '%m/%d/%Y %I:%M:%S %p %Z'
        for release in self.user_data['pEconomyModel']['TroopReleaseDates']:
            troop_id = release['TroopId']
            release_date = datetime.datetime.strptime(release['Date'], date_format).date()
            self.troops[troop_id]['release_date'] = release_date
            self.spoilers.append({'type': 'troop', 'date': release_date, 'id': troop_id})
        for release in self.user_data['pEconomyModel']['PetReleaseDates']:
            pet_id = release['PetId']
            release_date = datetime.datetime.strptime(release['Date'], date_format).date()
            self.pets[pet_id]['release_date'] = release_date
            self.spoilers.append({'type': 'pet', 'date': release_date, 'id': pet_id})
        for release in self.user_data['pEconomyModel']['KingdomReleaseDates']:
            kingdom_id = release['KingdomId']
            release_date = datetime.datetime.strptime(release['Date'], date_format).date()
            self.kingdoms[kingdom_id]['release_date'] = release_date
            self.spoilers.append({'type': 'kingdom', 'date': release_date, 'id': kingdom_id})
        for release in self.user_data['pEconomyModel']['HeroClassReleaseDates']:
            class_id = release['HeroClassId']
            release_date = datetime.datetime.strptime(release['Date'], date_format).date()
            self.classes[class_id]['release_date'] = release_date
            self.spoilers.append({'type': 'class', 'date': release_date, 'id': class_id})
        for release in self.user_data['pEconomyModel']['RoomReleaseDates']:
            room_id = release['RoomId']
            release_date = datetime.datetime.strptime(release['Date'], date_format).date()
            # self.rooms[room_id]['release_date'] = release_date
            self.spoilers.append({'type': 'room', 'date': release_date, 'id': room_id})
        for release in self.user_data['pEconomyModel']['WeaponReleaseDates']:
            weapon_id = release['WeaponId']
            release_date = datetime.datetime.strptime(release['Date'], date_format).date()
            self.weapons.setdefault(weapon_id, {})['release_date'] = release_date
            self.spoilers.append({'type': 'weapon', 'date': release_date, 'id': weapon_id})
        for release in self.user_data['BasicLiveEventArray']:
            result = {'start': datetime.datetime.utcfromtimestamp(release['StartDate']).date(),
                      'end': datetime.datetime.utcfromtimestamp(release['EndDate']).date(),
                      # 'id': release['Id'],
                      'type': self.EVENT_TYPES.get(release['Type'], release['Type']),
                      'names': release.get('Name'),
                      'gacha': release['GachaTroop'],
                      'kingdom_id': release.get('Kingdom')}
            self.events.append(result)

        self.events.sort(key=operator.itemgetter('start'))
        self.spoilers.sort(key=operator.itemgetter('date'))
