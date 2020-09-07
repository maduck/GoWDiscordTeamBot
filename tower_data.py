import json
import operator
import os
import threading

import discord

from util import bool_to_emoticon, merge


class TowerOfDoomData:
    TOWER_CONFIG_FILE = 'towerofdoom.json'

    DEFAULT_TOWER_DATA = {
        'rooms': {
            "ii": ["II", "r", "Rare"],
            "iii": ["III", "u", "ur", "ultrarare", "Ultra-Rare"],
            "iv": ["IV", "e", "Epic"],
            "v": ["V", "l", "Legendary"],
            "vi": ["VI", "m", "Mythic"]
        },
        'scrolls': {
            "armor": ["🛡️", "ar", "Armor"],
            "attack": ["⚔️", "at", "Attack"],
            "life": ["❤️", "li", "Life"],
            "magic": ["🔮", "ma", "Magic"],
            "haste": ["💨", "ha", "Haste"],
            "luck": ["🍀", "lu", "Luck"],
            "power": ["⚡", "po", "Power"],
            "unlock": ["🆙", "un", "Unlock"],
            "heroism": ["🦸", "he", "Heroism"],
            "fireball": ["🔥", "fi", "Fireball"],
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

    def __init__(self):
        self.__data = {}
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.TOWER_CONFIG_FILE):
            return
        lock = threading.Lock()
        with lock:
            with open(self.TOWER_CONFIG_FILE) as f:
                self.__data = json.load(f)

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
        if not str(guild.id) in self.__data:
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

    def get_key_from_alias(self, data, category, value):
        keys = self.DEFAULT_TOWER_DATA[category].keys()

        # Get the key from the alias.
        result = list(filter(lambda key: value.lower() in [i.lower() for i in data[category].get(key, [])], keys))
        if not result:
            return

        return result[0]

    def edit_floor(self, message, floor, room, scroll):
        # Returns tuple (Success, Message)

        # Includes default and server-custom data.
        my_data = self.get(message.guild)

        channel = str(message.channel.id)

        floor = int(floor)

        try:
            room_key = self.get_key_from_alias(my_data, 'rooms', room)
            room_display = my_data['rooms'][room_key][0]
        except KeyError:
            return False, f'Couldn\'t find room `{room}`'

        # Mythic room below floor 25? always a scroll.
        if floor <= 25 and room_key == "VI":
            return False, f'The boss room on floor {floor_number} always contains a Forge Scroll.'

        try:
            scroll_key = self.get_key_from_alias(my_data, 'scrolls', scroll)
            # Store the floor data.
            scroll_new_display = my_data["scrolls"][scroll_key][0]
            #
            # ACTUALLY SET THE DATA HERE.
            #
            scroll_old_key, scroll_new_key = self.set_scroll(message.guild, channel, floor, room_key, scroll_key)
        except KeyError as e:
            return False, f'Couldn\'t find scroll {scroll}'

        if scroll_old_key == 'unknown':
            return True, f'Set floor {floor} room {room_display} to {scroll_new_display}'
        else:
            scroll_old_display = my_data["scrolls"][scroll_old_key][0]
            return True, f'Replaced floor {floor} room {room_display} to {scroll_new_display} (was {scroll_old_display})'

    def format_floor(self, my_data, floor, floor_data):
        floor = int(floor)
        rooms = [
            f'{my_data["rooms"][r][0]} = {my_data["scrolls"].get(floor_data.get(r, "unknown"))[0]}'
            for r in self.DEFAULT_TOWER_DATA['rooms'].keys()
        ]
        for i, room in enumerate(self.DEFAULT_TOWER_DATA['rooms'].keys()):
            if floor_data.get(room, 'unknown') in my_data['hide']:
                rooms[i] = f'||{rooms[i]}||'

        # Hide the boss room (always a scroll)
        if floor <= 25:
            del rooms[4]

        return ', '.join(rooms)

    def format_output(self, guild, color, channel):
        my_data = self.get(guild)

        tower_data = my_data.get(str(channel.id), {}).items()

        if len(tower_data) == 0:
            e = discord.Embed(title='Tower of Doom', color=color)
            e.add_field(name=f'Failure',
                        value=f'Couldn\'t any data for #{channel.name}.\nPlease use `!towerhelp` for more info.')
            return e

        tower_data = sorted(tower_data, key=operator.itemgetter(0))

        display = {}
        for key in my_data["rooms"].keys():
            display[key] = my_data["rooms"][key][0]
        for key in my_data["scrolls"].keys():
            display[key] = my_data["scrolls"][key][0]

        e = discord.Embed(title='Tower of Doom', color=color)

        field_lines = []
        starting_floor = tower_data[0][0]
        field_header = channel.name
        for floor, floor_data in tower_data:
            line = f'Floor {floor}: {self.format_floor(my_data, floor, floor_data)}'
            if len(field_header) + len(line) + sum([len(fl) for fl in field_lines]) < 1024:
                field_lines.append(line)
            else:
                tower_text = '\n'.join(field_lines)
                e.add_field(name=field_header, value=tower_text, inline=False)
                field_lines = [line]
                starting_floor = floor
            field_header = f'Floors {starting_floor} - {floor}'
            if floor == starting_floor:
                field_header = f'Floor {floor}'
        tower_text = '\n'.join(field_lines)
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

        old_value = my_data.get(option, self.DEFAULT_TOWER_DATA[option])
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

        rooms_text = '\n'.join([
            f'II: {", ".join(my_data["rooms"]["ii"])}',
            f'III: {", ".join(my_data["rooms"]["iii"])}',
            f'IV: {", ".join(my_data["rooms"]["iv"])}',
            f'V: {", ".join(my_data["rooms"]["v"])}',
            f'VI: {", ".join(my_data["rooms"]["vi"])}',
        ])

        e.add_field(name='Rooms', value=rooms_text, inline=True)

        # TODO: Revise get() to make this cleaner.
        # f'Life: {", ".join(my_data["scrolls"]["life"])}',
        scrolls_text = '\n'.join(
            [
                f'{key.title()}: {", ".join(my_data["scrolls"][key.lower()])}'
                for key in self.DEFAULT_TOWER_DATA['scrolls'].keys()
            ])

        e.add_field(name='Scrolls', value=scrolls_text, inline=True)

        options_text = '\n'.join([
            f'**Short Format**: {bool_to_emoticon(my_data["short"])}',
            'Only respond to edits with a :thumbsup: instead of a full message.',
            f'**Hide Values**: {"None" if my_data["hide"] == [] else ",".join(my_data["hide"])}',
            'Hide unimportant scrolls with spoilers.'
        ])

        e.add_field(name='Options', value=options_text, inline=False)

        return e
