import discord
import json
import os
import threading

from base_bot import log
from util import atoi, merge, natural_keys, bool_to_emoticon


class TowerOfDoomData:
    TOWER_CONFIG_FILE = 'towerofdoom.json'

    DEFAULT_TOWER_DATA = {
        'rooms': {
            "II": ["II", "r", "Rare"],
            "III": ["III", "u", "ur", "ultrarare", "Ultra-Rare"],
            "IV": ["IV", "e", "Epic"],
            "V": ["V", "l", "Legendary"],
            "VI": ["VI", "m", "Mythic"]
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
        # Bypass .get() since that includes default data.
        my_data = self.__data.get(str(guild.id), {})

        old_values = my_data.get(
            category, self.DEFAULT_TOWER_DATA[category]
        ).get(
            field, self.DEFAULT_TOWER_DATA[category][field]
        )
        new_values = values.split(',')

        # Create a dict if it doesn't exist
        my_data[category] = my_data.get(category, {})
        my_data[category][field] = new_values
        self.set(guild, my_data)

        return ', '.join(old_values), ', '.join(new_values)

    def set_scroll(self, guild, channel, floor, room, scroll):
        # Bypass .get() since that includes default data.
        my_data = self.__data.get(str(guild.id), {})

        # Create a dict if it doesn't exist
        my_data[channel] = my_data.get(channel, {})
        my_data[channel][floor] = my_data[channel].get(floor, {})

        old_value = my_data[channel][floor].get(room, 'unknown')
        my_data[channel][floor][room] = scroll
        new_value = my_data[channel][floor].get(room, '<ERROR>')
        self.set(guild, my_data)

        return old_value, new_value

    def get(self, guild):
        # TODO: Make sure the config returns defaults for any unpopulated values,
        # while also avoiding writing defaults to save space.
        # I use lots of .get(key, default) to avoid 
        if guild is None:
            return {}
        return merge(dict(self.__data.get(str(guild.id), {})), self.DEFAULT_TOWER_DATA)

    def clear_data(self, prefix, guild, message):
        # Bypass .get() since that includes default data.
        my_data = self.__data.get(str(guild.id), {})
        channel = str(message.channel.id)

        # Override channel data with empty.
        my_data[channel] = {}
        self.set(guild, my_data)

    def get_key_from_alias(self, data, category, value):
        keys = self.DEFAULT_TOWER_DATA[category].keys()

        # Get the key from the alias.
        result = list(filter(lambda key: value.lower() in [i.lower() for i in data[category].get(key, [])], keys))
        if not result:
            return

        return result[0]

    def edit_floor(self, prefix, guild, message, floor, room, scroll):
        # Returns tuple (Success, Message)

        # Includes default and server-custom data.
        my_data = self.get(guild)

        channel = str(message.channel.id)

        # FIXME this should not be able to fire
        try:
            floor_number = atoi(floor)
        except Exception:
            # log.debug(f"Couldn't find floor {floor} in {my_data['floors']}")
            return f'Invalid floor {floor}'

        try:
            room_key = self.get_key_from_alias(my_data, 'rooms', room)
            room_display = my_data['rooms'][room_key][0]
        except KeyError:
            # log.debug(f"Couldn't find room {room} in {my_data['rooms']}")
            return False, f'Couldn\'t find room {room}'

        # Mythic room below floor 25? always a scroll.
        if floor_number <= 25 and room_key == "VI":
            return False, f'The boss room on floor {floor_number} always contains a Forge Scroll.'

        try:
            scroll_key = self.get_key_from_alias(my_data, 'scrolls', scroll)
            # Store the floor data.
            scroll_new_display = my_data["scrolls"][scroll_key][0]
            #
            # ACTUALLY SET THE DATA HERE.
            #
            scroll_old_key, scroll_new_key = self.set_scroll(guild, channel, floor, room_key, scroll_key)
        except KeyError as e:
            return False, f'Couldn\'t find scroll {scroll}'

        if scroll_old_key == 'unknown':
            return True, f'Set floor {floor} room {room_display} to {scroll_new_display}'
        else:
            scroll_old_display = my_data["scrolls"][scroll_old_key][0]
            return True, f'Replaced floor {floor} room {room_display} to {scroll_new_display} (was {scroll_old_display})'

    @staticmethod
    def format_floor(my_data, display, floor, floor_data):
        rooms = [
            f'{my_data["rooms"]["II"][0]} = {my_data["scrolls"].get(floor_data.get("II", "unknown"))[0]}, ',
            f'{my_data["rooms"]["III"][0]} = {my_data["scrolls"].get(floor_data.get("III", "unknown"))[0]}, ',
            f'{my_data["rooms"]["IV"][0]} = {my_data["scrolls"].get(floor_data.get("IV", "unknown"))[0]}, ',
            f'{my_data["rooms"]["V"][0]} = {my_data["scrolls"].get(floor_data.get("V", "unknown"))[0]}, ',
            f'{my_data["rooms"]["VI"][0]} = {my_data["scrolls"].get(floor_data.get("VI", "unknown"))[0]}'
        ]
        if floor_data.get('II', 'unknown') in my_data['hide']:
            rooms[0] = f"||{rooms[0]}||"
        if floor_data.get('III', 'unknown') in my_data['hide']:
            rooms[1] = f"||{rooms[1]}||"
        if floor_data.get('IV', 'unknown') in my_data['hide']:
            rooms[2] = f"||{rooms[2]}||"
        if floor_data.get('V', 'unknown') in my_data['hide']:
            rooms[3] = f"||{rooms[3]}||"
        if floor_data.get('VI', 'unknown') in my_data['hide']:
            rooms[4] = f"||{rooms[4]}||"

        # Hide the boss room (always a scroll)
        if int(floor) <= 25:
            del rooms[4]

        return ' '.join(rooms)

    def format_output(self, guild, color, channel):
        my_data = self.get(guild)

        tower_data = my_data.get(str(channel.id), {}).items()

        if len(tower_data) == 0:
            e = discord.Embed(title='Tower of Doom', color=color)
            e.add_field(name=f'Failure',
                        value=f'Couldn\'t any data for #{channel.name}.\nPlease use `!towerhelp` for more info.')
            return e

        tower_data = sorted(tower_data, key=natural_keys)

        # Get the display strings for rooms and scrolls.
        display = {}
        for key in my_data["rooms"].keys():
            display[key] = my_data["rooms"][key][0]
        for key in my_data["scrolls"].keys():
            display[key] = my_data["scrolls"][key][0]

        tower_text = '\n'.join([
            f'Floor {floor}: {self.format_floor(my_data, display, floor, floor_data)}' for floor, floor_data in
            tower_data
        ])

        if tower_text == "":
            e = discord.Embed(title='Tower of Doom', color=color)
            e.add_field(name=f'Failure',
                        value=f'Couldn\'t any data for #{channel.name}.\nPlease use `!towerhelp` for more info.')
            return e

        e = discord.Embed(title='Tower of Doom', color=color)
        e.add_field(name=f'#{channel.name}', value=tower_text)
        # log.warn(e.fields)
        return e

    def set_option(self, guild, option, value, boolean=False):
        # Bypass .get() since that includes default data.
        my_data = self.__data.get(str(guild.id), {})

        if option in ['short']:
            # String to boolean.
            value_parsed = value.lower() in ['true', '1', 't', 'y', 'yes']
        elif option in ['hide']:
            # String to list.
            if value == "none":
                value_parsed = []
            else:
                value_parsed = value.split(',')
        else:
            value_parsed = value

        old_value = my_data.get(option, self.DEFAULT_TOWER_DATA[option])
        my_data[option] = value_parsed
        new_value = my_data.get(option, '<ERROR>')
        self.set(guild, my_data)

        return old_value, new_value

    def format_output_config(self, prefix, guild, color):
        my_data = self.get(guild)
        e = discord.Embed(title='Tower of Doom Config', color=color)

        # log.info(my_data)

        help_text = '\n'.join([
            "To configure the aliases, provide a category and a list of values separated by commas.",
            f"`{prefix}towerconfig rooms rare r,rare,ii`"
        ])

        e.add_field(name='Help', value=help_text, inline=False)

        rooms_text = '\n'.join([
            f'Rare (II): {", ".join(my_data["rooms"]["II"])}',
            f'Ultra-Rare (III): {", ".join(my_data["rooms"]["III"])}',
            f'Epic (IV): {", ".join(my_data["rooms"]["IV"])}',
            f'Legendary (V): {", ".join(my_data["rooms"]["V"])}',
            f'Mythic (VI): {", ".join(my_data["rooms"]["VI"])}',
        ])

        e.add_field(name='Rooms', value=rooms_text, inline=True)

        # TODO: Revise get() to make this cleaner.
        # log.debug(my_data["scrolls"])
        scrolls_text = '\n'.join([
            f'Armor: {", ".join(my_data["scrolls"]["armor"])}',
            f'Attack: {", ".join(my_data["scrolls"]["attack"])}',
            f'Life: {", ".join(my_data["scrolls"]["life"])}',
            f'Magic: {", ".join(my_data["scrolls"]["magic"])}',
            f'Haste: {", ".join(my_data["scrolls"]["haste"])}',
            f'Luck: {", ".join(my_data["scrolls"]["luck"])}',
            f'Power: {", ".join(my_data["scrolls"]["power"])}',
            f'Unlock: {", ".join(my_data["scrolls"]["unlock"])}',
            f'Heroism: {", ".join(my_data["scrolls"]["heroism"])}',
            f'Fireball: {", ".join(my_data["scrolls"]["fireball"])}'
        ])

        e.add_field(name='Scrolls', value=scrolls_text, inline=True)

        options_text = '\n'.join([
            f'**Short Format**: {bool_to_emoticon(my_data["short"])}',
            'Only respond to edits with a :thumbs_up: instead of a full message.',
            f'**Hide Values**: {"None" if my_data["hide"] == [] else ",".join(my_data["hide"])}',
            'Hide unimportant scrolls with spoilers.'
        ])

        e.add_field(name='Options', value=options_text, inline=False)

        return e
