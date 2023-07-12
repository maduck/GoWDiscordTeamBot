import copy
import csv
import json
import operator
import os
import threading

import discord
import requests
from requests import HTTPError

from util import bool_to_emoticon, merge


class TowerOfDoomData:
    TOWER_CONFIG_FILE = 'towerofdoom.json'

    DEFAULT_TOWER_DATA = {
        'rooms': {
            "ii": ["II", "Rare"],
            "iii": ["III", "Ultra-Rare"],
            "iv": ["IV", "Epic"],
            "v": ["V", "Legendary"],
            "vi": ["VI", "Mythic"]
        },
        'scrolls': {
            "armor": ["🛡️", "Armor"],
            "attack": ["⚔️", "Attack"],
            "life": ["❤️", "Life"],
            "magic": ["🔮", "Magic"],
            "haste": ["💨", "Haste"],
            "luck": ["🍀", "Luck"],
            "power": ["⚡", "Power"],
            "unlock": ["🆙", "Unlock"],
            "heroism": ["🦸", "Heroism"],
            "fireball": ["🔥", "Fireball"],
            "unknown": ["❓", "?", "unknown"]
        },
        # Options.
        "short": False,
        "hide": [
            "armor",
            "attack",
            "life",
            "magic",
            "power"
        ],
    }

    def __init__(self, emojis):
        self.emojis = emojis
        self.__data = {}
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.TOWER_CONFIG_FILE):
            return
        lock = threading.Lock()
        with lock:
            with open(self.TOWER_CONFIG_FILE) as f:
                self.__data = json.load(f)
        self.make_floors_numeric()

    def make_floors_numeric(self):
        for guild in self.__data.keys():
            for channel in self.__data[guild].keys():
                # FIXME split up config and tower data, so those checks can be removed
                if isinstance(self.__data[guild][channel], dict) and all(
                    k.isdigit() for k in self.__data[guild][channel].keys()
                ):
                    self.__data[guild][channel] = {int(k): v for k, v in self.__data[guild][channel].items()
                                                   if k.isdigit()}

    def save_data(self):
        lock = threading.Lock()
        with lock:
            with open(self.TOWER_CONFIG_FILE, 'w') as f:
                json.dump(self.__data, f, sort_keys=True, indent=2)

    def set(self, guild, data):
        self.__data[str(guild.id)] = data
        self.save_data()

    def set_alias(self, guild, category, field, values):
        my_data = self.__data.get(str(guild.id), {})

        if category not in self.DEFAULT_TOWER_DATA:
            return None, None
        if field not in self.DEFAULT_TOWER_DATA[category]:
            return None, None

        category_data = my_data.setdefault(category.lower(), {})
        old_values = category_data.get(field.lower(), self.DEFAULT_TOWER_DATA[category][field])

        new_values = [v.strip() for v in values.split(',')]
        my_data[category][field] = new_values
        self.set(guild, my_data)

        return ', '.join(old_values), ', '.join(new_values)

    def set_scroll(self, guild, channel, floor, room, scroll):
        channel_data = self.__data.get(str(guild.id), {})

        channel_data[channel] = channel_data.get(channel, {})
        channel_data[channel][floor] = channel_data[channel].get(floor, {})

        old_value = channel_data[channel][floor].get(room, 'unknown')
        channel_data[channel][floor][room] = scroll
        new_value = channel_data[channel][floor].get(room, '<ERROR>')
        self.set(guild, channel_data)

        return old_value, new_value

    def get(self, guild):
        guild_data = self.__data.get(str(guild.id), {})
        return merge(guild_data, self.DEFAULT_TOWER_DATA)

    def reset_config(self, guild):
        if str(guild.id) not in self.__data:
            return

        config_entries = ('rooms', 'scrolls', 'short', 'hide')

        guild_data = self.__data[str(guild.id)]
        for entry in config_entries:
            if entry in guild_data:
                del guild_data[entry]
        self.set(guild, guild_data)

    def clear_data(self, message):
        guild_id = str(message.guild.id)
        if guild_id not in self.__data:
            return
        guild_data = self.__data[guild_id]
        channel = str(message.channel.id)
        if channel in guild_data:
            del guild_data[channel]

        self.set(message.guild, guild_data)

    def match_input_with_aliases(self, data, category, input_value):
        if not input_value:
            return None
        keys = self.DEFAULT_TOWER_DATA[category].keys()

        def matching_key(key):
            aliases = data[category].get(key, [])
            return any(a.lower().startswith(input_value.lower()) for a in aliases if input_value)

        return next(filter(matching_key, keys))

    def edit_floor(self, message, floor, room, scroll):
        """
        :rtype: tuple[bool, str]
        """

        my_data = self.get(message.guild)
        if not my_data:
            return True, ''
        channel = str(message.channel.id)
        if type(floor) != int and not floor.isdigit():
            return False, 'Invalid floor number'
        floor = int(floor)
        try:
            room_key = self.match_input_with_aliases(my_data, 'rooms', room)
            room_display = my_data['rooms'][room_key][0]
        except StopIteration:
            return False, f'Couldn\'t find room `{room}`'

        if floor <= 25 and room_key.lower() == "vi":
            return False, f'The boss room on floor {floor} always contains a Forge Scroll.'

        try:
            scroll_key = self.match_input_with_aliases(my_data, 'scrolls', scroll)
            if not scroll_key:
                return True, '-'
            scroll_new_display = my_data["scrolls"][scroll_key][0]
            scroll_old_key, scroll_new_key = self.set_scroll(message.guild, channel, floor, room_key, scroll_key)
        except StopIteration:
            return False, f'Couldn\'t find scroll `{scroll}`.'

        if scroll_old_key == 'unknown':
            return True, f'Set floor {floor} room {room_display} to {scroll_new_display}'
        scroll_old_display = my_data["scrolls"][scroll_old_key][0]
        return True, f'Replaced floor {floor} room {room_display} to {scroll_new_display} (was {scroll_old_display})'

    def format_floor(self, my_data, floor, floor_data):
        floor = int(floor)
        room_emojis = {
            'I': self.emojis.get('doomroom1'),
            'II': self.emojis.get('doomroom2'),
            'III': self.emojis.get('doomroom3'),
            'IV': self.emojis.get('doomroom4'),
            'V': self.emojis.get('doomroom5'),
        }
        rooms = [
            f'{room_emojis.get(my_data["rooms"][r][0], my_data["rooms"][r][0])} = '
            f'{my_data["scrolls"].get(floor_data.get(r, "unknown"))[0]}'
            for r in self.DEFAULT_TOWER_DATA['rooms'].keys()
        ]
        for i, room in enumerate(self.DEFAULT_TOWER_DATA['rooms'].keys()):
            if floor_data.get(room, 'unknown') in my_data['hide']:
                rooms[i] = f'||{rooms[i]}||'

        # Hide the boss room (always a scroll)
        if floor <= 25:
            del rooms[4]

        return ', '.join(rooms)

    def format_whole_floor(self, floor: int, guild_data, floor_data, shortened: bool):
        if shortened:
            return f'{self.format_short_floor(floor, floor_data)}'
        return f'Floor {floor}: {self.format_floor(guild_data, floor, floor_data)}'

    def format_output(self, guild, color, channel, prefix='!', _range=None, shortened=False):
        guild_data = self.get(guild)

        channel_data = guild_data.get(str(channel.id), {}).items()
        title = f'Tower of Doom overview for {channel}'

        if not channel_data:
            e = discord.Embed(title=title, color=color)
            e.add_field(name='Failure',
                        value=f'Couldn\'t find any data for #{channel.name}.\n'
                              f'Please use `{prefix}towerhelp` for more info.')
            return e

        channel_data = sorted(channel_data, key=operator.itemgetter(0))
        if _range:
            my_range = _range.split('-')
            channel_data = [floor for floor in channel_data if int(my_range[0]) <= floor[0] <= int(my_range[1])]
            if not channel_data:
                e = discord.Embed(title=title, color=color)
                e.add_field(name='Failure', value=f'No data for floors {_range}.')
                return e

        e = discord.Embed(title=title, color=color)

        field_lines = []
        starting_floor = channel_data[0][0]
        field_header = channel.name
        for floor, floor_data in channel_data:
            line = self.format_whole_floor(int(floor), guild_data, floor_data, shortened)
            if (
                len(field_header)
                + len(line)
                + sum(len(fl) + 1 for fl in field_lines)
                < 1024
            ):
                field_lines.append(line)
            else:
                tower_text = ('/' if shortened else '\n').join(field_lines)
                e.add_field(name=field_header, value=tower_text, inline=False)
                field_lines = [line]
                starting_floor = floor
            field_header = f'Floors {starting_floor} - {floor}'
            if floor == starting_floor:
                field_header = f'Floor {floor}'
        tower_text = ('/' if shortened else '\n').join(field_lines)
        e.add_field(name=field_header, value=tower_text, inline=False)
        return e

    def set_option(self, guild, option, value):
        value_map = {
            'short': value.lower() in ['true', '1', 't', 'y', 'yes', 'on'],
            'hide': [v.strip() for v in value.split(',') if v.lower().strip() != 'none'],
        }

        if option.lower() not in value_map.keys():
            return None, None

        my_data = self.__data.get(str(guild.id), {})

        defaults = copy.deepcopy(self.DEFAULT_TOWER_DATA)
        old_value = my_data.get(option, defaults[option])
        my_data[option] = value_map[option]
        self.set(guild, my_data)

        new_value = my_data.get(option, '<ERROR>')
        return old_value, new_value

    def format_output_config(self, prefix, guild, color):
        my_data = self.get(guild)

        e = discord.Embed(title='Tower of Doom Config', color=color)
        help_text = '\n'.join([
            "To configure the aliases, provide a category and a list of values separated by commas.",
            f"`{prefix}towerconfig rooms rare r,rare,ii`"
        ])
        e.add_field(name='Help', value=help_text, inline=False)
        rooms_text = '\n'.join([f'{r.upper()}: {", ".join(my_data["rooms"][r])}'
                                for r in self.DEFAULT_TOWER_DATA['rooms']])
        e.add_field(name='Rooms', value=rooms_text, inline=True)

        scrolls_text = '\n'.join(
            [
                f'{key.title()}: {", ".join(my_data["scrolls"][key.lower()])}'
                for key in self.DEFAULT_TOWER_DATA['scrolls'].keys()
            ])
        e.add_field(name='Scrolls', value=scrolls_text, inline=True)
        hidden_values = ', '.join(v.title() for v in my_data['hide']) if my_data['hide'] else 'None'

        options_text = '\n'.join([
            f'**Short Format**: {bool_to_emoticon(my_data["short"])}',
            'Only respond to edits with a :thumbsup: instead of a full message.',
            f'**Hide Values**: {hidden_values}',
            'Hide unimportant scrolls with spoilers.'
        ])
        e.add_field(name='Options', value=options_text, inline=False)
        return e

    @staticmethod
    def format_short_floor(floor, floor_data):
        if unlock_rooms := [
            room for room, contents in floor_data.items() if contents == 'unlock'
        ]:
            unlock_room = unlock_rooms[0]
        else:
            unlock_room = '?'
        return f'{floor}:{unlock_room}'

    def download_from_taran(self, message, map_name, version, token=''):
        headers = {'user-agent': f'garyatrics.com-discord-bot-{version}'}
        download_url = f'https://www.taransworld.com/DoomMap/main.pl?mapName={map_name.upper()}&txt=1&token={token}'
        try:
            r = requests.get(download_url, headers=headers)
            r.raise_for_status()
        except HTTPError:
            return discord.Embed(title='Error', description=f'Map {map_name} not found.',
                                 color=discord.Color.from_rgb(0, 0, 0))
        except requests.exceptions.ConnectionError as e:
            return discord.Embed(title='Error', description=f'Map {map_name} could not be downloaded: `{e.strerror}`',
                                 color=discord.Color.from_rgb(0, 0, 0))
        decoded_content = r.content.decode('utf-8')

        rooms = {
            '0': 'ii',
            '1': 'iii',
            '2': 'iv',
            '3': 'v',
            '4': 'vi',
        }
        scrolls = {
            'Armour': 'Armor',
        }

        csv_lines = csv.reader(decoded_content.splitlines())
        imported_floors = set()
        errors = 0
        for row in csv_lines:
            floor = row[0]
            room = rooms[row[1]]
            scroll = scrolls.get(row[2], row[2])
            result = self.edit_floor(message, floor, room, scroll)
            if result[0]:
                imported_floors.add(floor)
            else:
                errors += 1

        self.save_data()
        return self.render_import_result(len(imported_floors), errors)

    @staticmethod
    def render_import_result(floors, errors):
        message = f'Imported {floors} floors from [Taran\'s DoomMap](https://www.taransworld.com/DoomMap/).'
        if errors:
            message += f'\n\n{errors} fields could not be updated due to non-matching names.\n' \
                       f'Please make sure that your towerconfig contains the default' \
                       f' English names for scrolls and rooms.'
        return discord.Embed(title='Import result', description=message, color=discord.Color.from_rgb(255, 255, 255))
