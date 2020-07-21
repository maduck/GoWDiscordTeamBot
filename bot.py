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
    BASE_GUILD = 'GoW Bot Dev'
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
        log.debug(f'Active in {", ".join([g.name for g in self.guilds])}')
        game = discord.Game("Gems of War")
        await self.change_presence(status=discord.Status.idle, activity=game)
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
                          '3,1,1,1,3,1,1,14007]` '
                          '• __Mini format__: Put a "-" in front of the code to make it appear in a small box, '
                          'e.g. `-[1075,6251,6699,6007]`, or with language `de-[1075,6251,6699,6007]`.',
                    inline=False)
        e.add_field(name='─────────────────────────────────────', value='┈')
        e.add_field(name='Troop search',
                    value=f'• __Basics__: enter `{my_prefix}troop <search>`, e.g. `{my_prefix}troop elemaugrim`.\n'
                          f'• __Rules__:\n'
                          f'  - Search both works for troop ids and parts of their names.\n'
                          f'  - Search is _not_ case sensitive.\n'
                          f'  - Multiple results will show a list of matched troops.\n'
                          f'  - Spaces and apostrophes (\') don\'t matter.\n\n'
                          f'• __Language support__: All GoW languages are supported, put the two country code letters '
                          f'(en, fr, de, ru, it, es, cn) in front of the command, e.g. `de{my_prefix}troop '
                          f'elemaugrim`. Localized searches will only look for troop names with their respective '
                          f'translations.',
                    inline=False)
        e.add_field(name='─────────────────────────────────────', value='┈')
        e.add_field(name='Weapon search',
                    value=f'• __Basics__: enter `{my_prefix}weapon <search>`, e.g. `{my_prefix}weapon cog`.\n'
                          f'• __Rules__:\n'
                          f'  - Search both works for weapon ids and parts of their names.\n'
                          f'  - Search is _not_ case sensitive.\n'
                          f'  - Multiple results will show a list of matched troops.\n'
                          f'  - Spaces and apostrophes (\') don\'t matter.\n\n'
                          f'• __Language support__: All GoW languages are supported, put the two country code letters '
                          f'(en, fr, de, ru, it, es, cn) in front of the command, e.g. `de{my_prefix}weapon cog`. '
                          f'Localized searches will only look for weapon names with their respective translations.',
                    inline=False)
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
                talents = [f'**{t["name"]}** ({t["description"]})' for t in tree]
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
            message_lines = [
                f'Kingdom: {pet["kingdom_id"]}',
                ', '.join(pet['colors']),
            ]
            e.add_field(name=f'{pet["name"]} `#{pet["id"]}`', value='\n'.join(message_lines))

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
                f'**{weapon["kingdom_title"]}** {weapon["kingdom"]}',
                f'**{weapon["rarity_title"]}** {weapon["rarity"]}',
                f'**{weapon["roles_title"]}** {", ".join(weapon["roles"])}',
                f'**{weapon["type_title"]}** {weapon["type"]}',
            ]
            e.add_field(name=f'{weapon["spell"]["cost"]}{mana} {weapon["name"]} `#{weapon["id"]}`', value='\n'.join(message_lines))
        else:
            color = discord.Color.from_rgb(255, 255, 255)
            e = discord.Embed(title='Weapon search', color=color)
            weapons_found = '\n'.join([f'{w["name"]} ({w["id"]})' for w in result])
            e.add_field(name=f'{search_term} matches more than one weapon.', value=weapons_found)
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
            color = discord.Color.from_rgb(*rarity_color)
            e = discord.Embed(title='Troop search', color=color)
            mana = self.my_emojis.get(troop['color_code'])
            message_lines = [
                troop["description"],
                '',
                f'**{troop["spell_title"]}** {troop["spell"]["name"]}: {troop["spell"]["description"]}',
                '',
                f'**{troop["kingdom_title"]}** {troop["kingdom"]}',
                f'**{troop["rarity_title"]}** {troop["rarity"]}',
                f'**{troop["roles_title"]}** {", ".join(troop["roles"])}',
                f'**{troop["type_title"]}** {troop["type"]}',
            ]
            e.add_field(name=f'{troop["spell"]["cost"]}{mana} {troop["name"]} `#{troop["id"]}`', value='\n'.join(message_lines))
            trait_list = [f'**{trait["name"]}** - {trait["description"]}' for trait in troop['traits']]
            traits = '\n'.join(trait_list)
            e.add_field(name=troop["traits_title"], value=traits, inline=False)
        else:
            color = discord.Color.from_rgb(255, 255, 255)
            e = discord.Embed(title=f'Troop search `{search_term}` found {len(result)} matches.', color=color)
            troops_found = [f'{t["name"]} ({t["id"]})' for t in result]
            troop_chunks = chunks(troops_found, 30)
            """
            if len(troops_found) > 1024:
                troops_found = troops_found[:992] + '\n...\n(list too long to display)'
            """
            for i, chunk in enumerate(troop_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)

        await message.channel.send(embed=e)

    async def handle_team_code(self, message, shortend=False):
        team = self.expander.get_team_from_message(message.content)
        if not team:
            log.debug(f'nothing found in message {message.content}')
            return
        log.debug(f'[{message.guild.id}][{message.channel}] sending team result to {message.author.display_name}')
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
            e.add_field(name=f'{team["class_title"]}: {team["class"]}', value='\n'.join(team['talents']),
                        inline=False)
        return e

    def format_output_team_shortend(self, team, color):
        e = discord.Embed(color=color)
        troops = [f'{t[1]}' for t in team['troops']]
        e.title = ', '.join(troops)

        if team['banner']:
            banner_texts = [f'{self.my_emojis.get(d[0], f":{d[0]}:")} {abs(d[1]) * f"{d[1]:+d}"[0]}' for d in
                            team['banner']['description']]
            banner = '{banner_name} {banner_texts}'.format(
                banner_name=team['banner']['name'],
                banner_texts=' '.join(banner_texts)
            )
            e.description = banner
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


if __name__ == '__main__':
    client = DiscordBot()
    client.run(TOKEN)
