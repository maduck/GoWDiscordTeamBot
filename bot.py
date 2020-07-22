#!/usr/bin/env python3
import json
import logging
import os
import re
import threading

import discord

from team_expando import TeamExpander

TOKEN = os.getenv('DISCORD_TOKEN')
LOGLEVEL = logging.DEBUG

formatter = logging.Formatter('%(asctime)-15s [%(levelname)s] %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(LOGLEVEL)
log = logging.getLogger(__name__)

log.setLevel(logging.DEBUG)
log.addHandler(handler)

RARITY_COLORS = {
    'Common': (255, 254, 255),
    'Uncommon': (84, 168, 31),
    'Rare': (32, 113, 254),
    'UltraRare': (150, 54, 232),
    'Epic': (246, 161, 32),
    'Legendary': (19, 227, 246),
    'Mythic': (19, 227, 246),
    'Doomed': (186, 0, 0),
}


def chunks(iterable, chunk_size):
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i:i + chunk_size]


async def pluralize_author(author):
    if author[-1] == 's':
        author += "'"
    else:
        author += "'s"
    return author


class DiscordBot(discord.Client):
    DEFAULT_PREFIX = '!'
    PREFIX_CONFIG_FILE = 'prefixes.json'
    BOT_NAME = 'Garys GoW Team Bot'
    BASE_GUILD = 'Garyatrics'
    VERSION = '0.2'
    SEARCH_COMMANDS = (
        {'key': 'troop',
         'search': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.)troop (?P<search>.*)$')},
        {'key': 'weapon',
         'search': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.)weapon (?P<search>.*)$')},
        {'key': 'kingdom',
         'search': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.)kingdom (?P<search>.*)$')},
        {'key': 'pet',
         'search': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.)pet (?P<search>.*)$')},
        {'key': 'class',
         'search': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.)class (?P<search>.*)$')},
    )

    def __init__(self, *args, **kwargs):
        log.debug(f'--------------------------- Starting {self.BOT_NAME} v{self.VERSION} --------------------------')
        super().__init__(*args, **kwargs)
        self.permissions = self.generate_permissions()
        self.invite_url = 'https://discordapp.com/api/oauth2/authorize?client_id={{}}&scope=bot&permissions={}'
        self.invite_url = self.invite_url.format(self.permissions.value)
        self.my_emojis = {}
        self.expander = TeamExpander()
        self.prefixes = {}
        self.load_prefixes()

    @staticmethod
    def generate_permissions():
        permissions = discord.Permissions.none()
        needed_permissions = [
            'add_reactions',
            'read_messages',
            'send_messages',
            'manage_messages',
            'read_message_history',
            'external_emojis',
        ]
        for perm_name in needed_permissions:
            setattr(permissions, perm_name, True)
        log.debug(f'Permissions required: {", ".join([p for p, v in permissions if v])}')
        return permissions

    async def on_ready(self):
        self.invite_url = self.invite_url.format(self.user.id)
        log.debug(f'Logged in as {self.user.name}')
        log.info(f'Invite with: {self.invite_url}')

        guilds = [g.name for g in self.guilds if g]
        log.debug(f'Active in {len(guilds)} guilds: {", ".join(guilds)}')

        game = discord.Game("Gems of War")
        await self.change_presence(status=discord.Status.online, activity=game)
        await self.update_base_emojis()

    async def update_base_emojis(self):
        for guild in self.guilds:
            if guild.name == self.BASE_GUILD:
                for emoji in guild.emojis:
                    self.my_emojis[emoji.name] = str(emoji)

    async def show_help(self, message):
        my_prefix = self.get_my_prefix(message.guild)
        e = discord.Embed(title='help')
        e.add_field(name='Team codes',
                    value='• __Basics__: Just post your team codes, e.g. `[1075,6251,6699,6007,3010,3,1,1,1,3,1,1,'
                          '14007]`. The bot will automatically answer with the troops posted in the code. The code '
                          'can be embedded within more text, and does not need to stand alone.\n\n'
                          '• __Language support__: All GoW languages are supported, put the two country code letters '
                          '(en, fr, de, ru, it, es, cn) in front of the team code, e.g. `cn[1075,6251,6699,6007,3010,'
                          '3,1,1,1,3,1,1,14007]`\n\n'
                          '• __Mini format__: Put a "-" in front of the code to make it appear in a small box, '
                          'e.g. `-[1075,6251,6699,6007]`, or with language `de-[1075,6251,6699,6007]`.',
                    inline=False)
        e.add_field(name='─────────────────────────────────────', value='┈')
        e.add_field(name='Searches',
                    value=f'• __Basics__: the following searches are supported:\n'
                          f' - `{my_prefix}troop <search>`, e.g. `{my_prefix}troop elemaugrim`.\n'
                          f' - `{my_prefix}weapon <search>`, e.g. `{my_prefix}weapon mang`.\n'
                          f' - `{my_prefix}pet <search>`, e.g. `{my_prefix}weapon mang`.\n'
                          f' - `{my_prefix}class <search>`, e.g. `{my_prefix}class archer`.\n'
                          f' - `{my_prefix}kingdom <search>`, e.g. `{my_prefix}kingdom karakoth`.\n'
                          f'• __Rules__:\n'
                          f'  - Search both works for ids and parts of their names.\n'
                          f'  - Search is _not_ case sensitive.\n'
                          f'  - Spaces, apostrophes (\') and dashes (-) will be ignored.\n\n'
                          f'  - Multiple results will show a list of matched troops.\n'
                          f'If one matching item is found, the side color will reflect the troop\'s base rarity.\n\n'
                          f'• __Language support__: All GoW languages are supported, put the two country code letters '
                          f'(en, fr, de, ru, it, es, cn) in front of the command, e.g. `de{my_prefix}troop '
                          f'elemaugrim`. Localized searches will only look for troop names with their respective '
                          f'translations.',
                    inline=False)
        e.add_field(name='─────────────────────────────────────', value='┈')
        e.add_field(name='Prefix',
                    value=f'• __Basics__: enter `{my_prefix}prefix <new_prefix>` to set a new prefix. Only the server' \
                          f'owner can do that.', inline=False)
        e.add_field(name='Quickhelp',
                    value=f'• __Basics__: enter `{my_prefix}quickhelp` to open a short overview of all commands.\n',
                    inline=False)
        await message.channel.send(embed=e)

    async def show_quickhelp(self, message):
        my_prefix = self.get_my_prefix(message.guild)
        e = discord.Embed(title='quickhelp')
        e.description = (
            f'`{my_prefix}help` complete help\n'
            f'`{my_prefix}quickhelp` this command\n'
            f'`{my_prefix}invite`\n'
            f'`[<troopcode>]` post team\n'
            f'`-[<troopcode>]` post team (short)\n'
            f'`{my_prefix}troop <search>`\n'
            f'`{my_prefix}weapon <search>`\n'
            f'`{my_prefix}pet <search>`\n'
            f'`{my_prefix}class <search>`\n'
            f'`{my_prefix}kingdom <search>`\n'
            f'`<language><command>` language support\n'
        )
        await message.channel.send(embed=e)

    async def on_guild_join(self, guild):
        log.debug(f'Joined guild {guild} (id {guild.id}).')

    async def on_guild_remove(self, guild):
        log.debug(f'Guild {guild} (id {guild.id}) kicked me out.')

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return

        my_prefix = self.get_my_prefix(message.guild)
        user_command = message.content.lower().strip()
        if user_command == f'{my_prefix}help':
            await self.show_help(message)
        elif user_command == f'{my_prefix}quickhelp':
            await self.show_quickhelp(message)
        elif user_command == f'{my_prefix}invite':
            await self.show_invite_link(message)
        elif user_command.startswith(f'{my_prefix}prefix '):
            await self.change_prefix(message, user_command)
        elif user_command == f'{my_prefix}prefix':
            await self.show_prefix(message)
        for command in self.SEARCH_COMMANDS:
            match = command['search'].match(user_command)
            if match:
                groups = match.groupdict()
                if groups['prefix'] != my_prefix:
                    return
                function_name = f'handle_{command["key"]}_search'
                search_function = getattr(self, function_name)
                search_term = groups['search']
                lang = groups['lang']
                await search_function(message, search_term, lang)
                return
        if "-[" in message.content:
            await self.handle_team_code(message, shortend=True)
        elif "[" in message.content:
            await self.handle_team_code(message)

    async def show_invite_link(self, message):
        color = discord.Color.from_rgb(255, 255, 255)
        e = discord.Embed(title='Bot invite link', color=color)
        link = 'https://discordapp.com/api/oauth2/authorize?client_id=733399051797790810&scope=bot&permissions=339008'
        e.add_field(name='Feel free to share!', value=link)
        await message.channel.send(embed=e)

    async def change_prefix(self, message, user_command):
        my_prefix = self.get_my_prefix(message.guild)
        issuing_user = message.author
        guild_owner = message.guild.owner
        if issuing_user == guild_owner:
            new_prefix = user_command[len(f'{my_prefix}prefix '):]
            self.prefixes[str(message.guild.id)] = new_prefix
            self.save_prefixes()
            color = discord.Color.from_rgb(255, 0, 0)
            e = discord.Embed(title='ADMINISTRATIVE CHANGE', color=color)
            e.add_field(name='Prefix change', value=f'Prefix was changed from `{my_prefix}` to `{new_prefix}`')
            await message.channel.send(embed=e)
            log.debug(f'[{message.guild.name}] Changed prefix from {my_prefix} to {new_prefix}')
        else:
            color = discord.Color.from_rgb(0, 0, 0)
            e = discord.Embed(title='There was a problem', color=color)
            e.add_field(name='Prefix change', value=f'Only the server owner has permission to change the prefix.')
            await message.channel.send(embed=e)

    def get_my_prefix(self, guild):
        if guild is None:
            return self.DEFAULT_PREFIX

        return self.prefixes.get(str(guild.id), self.DEFAULT_PREFIX)

    async def handle_kingdom_search(self, message, search_term, lang):
        result = self.expander.search_kingdom(search_term, lang)
        if not result:
            color = discord.Color.from_rgb(0, 0, 0)
            e = discord.Embed(title='Kingdom search', color=color)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            kingdom = result[0]
            e = discord.Embed(title='Kingdom search')
            message_lines = [
                kingdom['punchline'],
                kingdom['description'],
            ]
            e.add_field(name=f'{kingdom["name"]} `#{kingdom["id"]}`', value='\n'.join(message_lines))

        await message.channel.send(embed=e)

    async def handle_class_search(self, message, search_term, lang):
        result = self.expander.search_class(search_term, lang)
        if not result:
            color = discord.Color.from_rgb(0, 0, 0)
            e = discord.Embed(title='Class search', color=color)
            e.add_field(name=search_term, value='did not yield any result.')
        elif len(result) == 1:
            _class = result[0]
            e = discord.Embed(title='Class search')
            class_lines = [
                _class['kingdom'],
                _class['weapon'],
                _class['type'],
            ]
            e.add_field(name=f'{_class["name"]} `#{_class["id"]}`', value='\n'.join(class_lines), inline=False)
            for i, tree in enumerate(_class['talents']):
                talents = [f'**{t["name"]}**: ({t["description"]})' for t in tree]
                e.add_field(name=_class['trees'][i], value='\n'.join(talents), inline=True)
        await message.channel.send(embed=e)

    async def handle_pet_search(self, message, search_term, lang):
        result = self.expander.search_pet(search_term, lang)
        if not result:
            color = discord.Color.from_rgb(0, 0, 0)
            e = discord.Embed(title='Pet search', color=color)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            pet = result[0]
            e = discord.Embed(title='Pet search')
            mana = self.my_emojis.get(pet['color_code'])
            message_lines = [
                f'Kingdom: {pet["kingdom"]}',
            ]
            e.add_field(name=f'{mana} {pet["name"]} `#{pet["id"]}`', value='\n'.join(message_lines))
        else:
            color = discord.Color.from_rgb(255, 255, 255)
            e = discord.Embed(title=f'Pet search for `{search_term}` found {len(result)} matches.', color=color)
            pets_found = [f'{pet["name"]} ({pet["id"]})' for pet in result]
            weapon_chunks = chunks(pets_found, 30)
            for i, chunk in enumerate(weapon_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await message.channel.send(embed=e)

    async def handle_weapon_search(self, message, search_term, lang):
        result = self.expander.search_weapon(search_term, lang)
        if not result:
            color = discord.Color.from_rgb(0, 0, 0)
            e = discord.Embed(title='Weapon search', color=color)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            weapon = result[0]
            rarity_color = RARITY_COLORS.get(weapon['raw_rarity'], RARITY_COLORS['Mythic'])
            color = discord.Color.from_rgb(*rarity_color)
            e = discord.Embed(title='Weapon search', color=color)
            mana = self.my_emojis.get(weapon['color_code'])
            message_lines = [
                weapon['spell']['description'],
                '',
                f'**{weapon["kingdom_title"]}**: {weapon["kingdom"]}',
                f'**{weapon["rarity_title"]}**: {weapon["rarity"]}',
                f'**{weapon["roles_title"]}**: {", ".join(weapon["roles"])}',
                f'**{weapon["type_title"]}**: {weapon["type"]}',
                '',
                weapon['requirement_text'],
            ]
            e.add_field(name=f'{weapon["spell"]["cost"]}{mana} {weapon["name"]} `#{weapon["id"]}`',
                        value='\n'.join(message_lines))
        else:
            color = discord.Color.from_rgb(255, 255, 255)
            e = discord.Embed(title=f'Weapon search for `{search_term}` found {len(result)} matches.', color=color)
            weapons_found = [f'{t["name"]} ({t["id"]})' for t in result]
            weapon_chunks = chunks(weapons_found, 30)
            for i, chunk in enumerate(weapon_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await message.channel.send(embed=e)

    async def handle_troop_search(self, message, search_term, lang):
        result = self.expander.search_troop(search_term, lang)

        if not result:
            color = discord.Color.from_rgb(0, 0, 0)
            e = discord.Embed(title='Troop search', color=color)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            troop = result[0]
            rarity_color = RARITY_COLORS.get(troop['raw_rarity'], RARITY_COLORS['Mythic'])
            if 'Boss' in troop['raw_types']:
                rarity_color = RARITY_COLORS['Doomed']
            color = discord.Color.from_rgb(*rarity_color)
            e = discord.Embed(title='Troop search', color=color)
            e.set_thumbnail(url=troop['filename'])
            message_lines = [
                f'**{troop["spell"]["name"]}**: {troop["spell"]["description"]}',
                '',
                f'**{troop["kingdom_title"]}**: {troop["kingdom"]}',
                f'**{troop["rarity_title"]}**: {troop["rarity"]}',
                f'**{troop["roles_title"]}**: {", ".join(troop["roles"])}',
                f'**{troop["type_title"]}**: {troop["type"]}',
            ]
            mana = self.my_emojis.get(troop['color_code'])
            mana_display = f'{troop["spell"]["cost"]}{mana} '
            description = ''
            if troop['description']:
                description = f' *{troop["description"]}*'
            e.add_field(name=f'{mana_display}{troop["name"]} `#{troop["id"]}`{description}',
                        value='\n'.join(message_lines))
            trait_list = [f'**{trait["name"]}**: {trait["description"]}' for trait in troop['traits']]
            traits = '\n'.join(trait_list)
            e.add_field(name=troop["traits_title"], value=traits, inline=False)
        else:
            color = discord.Color.from_rgb(255, 255, 255)
            e = discord.Embed(title=f'Troop search for `{search_term}` found {len(result)} matches.', color=color)
            troops_found = [f'{t["name"]} ({t["id"]})' for t in result]
            troop_chunks = chunks(troops_found, 30)
            for i, chunk in enumerate(troop_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)

        await message.channel.send(embed=e)

    async def handle_team_code(self, message, shortend=False):
        team = self.expander.get_team_from_message(message.content)
        if not team:
            log.debug(f'nothing found in message {message.content}')
            return
        log.debug(f'[{message.guild.name}][{message.channel}] sending team result to {message.author.display_name}')
        color = discord.Color.from_rgb(19, 227, 246)
        author = message.author.display_name
        author = await pluralize_author(author)

        if shortend:
            e = self.format_output_team_shortend(team, color)
        else:
            e = self.format_output_team(team, color, author)

        await message.channel.send(embed=e)

    def format_output_team(self, team, color, author):
        e = discord.Embed(title=f"{author} team", color=color)
        troops = [f'{self.my_emojis.get(t[0], f":{t[0]}:")} {t[1]}' for t in team['troops']]
        team_text = '\n'.join(troops)
        e.add_field(name=team['troops_title'], value=team_text, inline=True)
        if team['banner']:
            banner_texts = [f'{self.my_emojis.get(d[0], f":{d[0]}:")} {abs(d[1]) * f"{d[1]:+d}"[0]}' for d in
                            team['banner']['description']]
            e.add_field(name=team['banner']['name'], value='\n'.join(banner_texts), inline=True)
        if team['class']:
            talents = '\n'.join(team['talents'])
            if all([t == '-' for t in team['talents']]):
                talents = '-'
            e.add_field(name=f'{team["class_title"]}: {team["class"]}', value=talents,
                        inline=False)
        return e

    def format_output_team_shortend(self, team, color):
        e = discord.Embed(color=color)
        troops = [f'{t[1]}' for t in team['troops']]
        e.title = ', '.join(troops)
        descriptions = []

        if team['class']:
            descriptions.append(team["class"])
        if team['banner']:
            banner_texts = [f'{self.my_emojis.get(d[0], f":{d[0]}:")}{abs(d[1]) * f"{d[1]:+d}"[0]}' for d in
                            team['banner']['description']]
            banner = '{banner_name} {banner_texts}'.format(
                banner_name=team['banner']['name'],
                banner_texts=' '.join(banner_texts)
            )
            descriptions.append(banner)
        if team['talents'] and not all([i == '-' for i in team['talents']]):
            descriptions.append(', '.join(team['talents']))
        e.description = '\n'.join(descriptions)
        return e

    def save_prefixes(self):
        lock = threading.Lock()
        with lock:
            with open(self.PREFIX_CONFIG_FILE, 'w') as f:
                json.dump(self.prefixes, f, sort_keys=True, indent=2)

    def load_prefixes(self):
        if not os.path.exists(self.PREFIX_CONFIG_FILE):
            return
        lock = threading.Lock()
        with lock:
            with open(self.PREFIX_CONFIG_FILE) as f:
                self.prefixes = json.load(f)

    async def show_prefix(self, message):
        my_prefix = self.get_my_prefix(message.guild)
        color = discord.Color.from_rgb(255, 255, 255)
        e = discord.Embed(title='Prefix', color=color)
        e.add_field(name='The current prefix is', value=f'`{my_prefix}`')
        await message.channel.send(embed=e)


if __name__ == '__main__':
    client = DiscordBot()
    client.run(TOKEN)
