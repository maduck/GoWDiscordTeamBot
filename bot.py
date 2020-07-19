#!/usr/bin/env python3
import logging
import os
import re

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
    'Rare': (84, 168, 31),
    'Uncommon': (84, 168, 31),
    'UltraRare': (32, 113, 254),
    'Epic': (151, 54, 232),
    'Legendary': (246, 161, 32),
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


async def show_help(message):
    e = discord.Embed(title='help')
    e.add_field(name='Team codes',
                value='• __Basics__: Just post your team codes, e.g. `[1075,6251,6699,6007,3010,3,1,1,1,3,1,1,'
                      '14007]`. The bot will automatically answer with the troops posted in the code. The code can be '
                      'embedded within more text, and does not need to stand alone.\n\n '
                      '• __Language support__: All GoW languages are supported, put the two country code letters (en, '
                      'fr, de, ru, it, es, cn) in front of the team code, e.g. `de[1075,6251,6699,6007,3010,3,1,1,1,'
                      '3,1,1,14007]`',
                inline=False)
    e.add_field(name='─────────────────────────────────────', value='┈')
    e.add_field(name='Troop search',
                value='• __Basics__: enter `!troop <search>`, e.g. `!troop elemaugrim`.\n'
                      '• __Rules__:\n'
                      '  - Search both works for troop ids and parts of their names.\n'
                      '  - Search is _not_ case sensitive.\n'
                      '  - Multiple results will show a list of matched troops.\n'
                      '  - Spaces and apostrophes (\') don\'t matter.\n\n'
                      '• __Language support__: All GoW languages are supported, put the two country code letters (en, '
                      'fr, de, ru, it, es, cn) in front of the command, e.g. `de!troop elemaugrim`. Localized '
                      'searches will only look for troop names with their respective translations.',
                inline=False)
    e.add_field(name='─────────────────────────────────────', value='┈')
    e.add_field(name='Weapon search',
                value='• __Basics__: enter `!weapon <search>`, e.g. `!weapon cog`.\n'
                      '• __Rules__:\n'
                      '  - Search both works for weapon ids and parts of their names.\n'
                      '  - Search is _not_ case sensitive.\n'
                      '  - Multiple results will show a list of matched troops.\n'
                      '  - Spaces and apostrophes (\') don\'t matter.\n\n'
                      '• __Language support__: All GoW languages are supported, put the two country code letters (en, '
                      'fr, de, ru, it, es, cn) in front of the command, e.g. `de!weapon cog`. Localized '
                      'searches will only look for weapon names with their respective translations.',
                inline=False)
    await message.channel.send(embed=e)


class DiscordBot(discord.Client):
    BOT_NAME = 'Garys GoW Team Bot'
    BASE_GUILD = 'GoW Bot Dev'
    VERSION = '0.2'
    SEARCH_COMMANDS = (
        {'key': 'troop',
         'search': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?!troop (?P<search>.*)$')},
        {'key': 'weapon',
         'search': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?!weapon (?P<search>.*)$')},
    )

    def __init__(self, *args, **kwargs):
        log.debug(f'--------------------------- Starting {self.BOT_NAME} v{self.VERSION} --------------------------')
        super().__init__(*args, **kwargs)
        self.permissions = self.generate_permissions()
        self.invite_url = 'https://discordapp.com/api/oauth2/authorize?client_id={{}}&scope=bot&permissions={}'
        self.invite_url = self.invite_url.format(self.permissions.value)
        self.my_emojis = {}
        self.expander = TeamExpander()

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
        await self.update_base_emojis()

    async def update_base_emojis(self):
        for guild in self.guilds:
            if guild.name == self.BASE_GUILD:
                for emoji in guild.emojis:
                    self.my_emojis[emoji.name] = str(emoji)

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        if message.content.lower().strip() == '!help':
            await show_help(message)
        for command in self.SEARCH_COMMANDS:
            match = command['search'].match(message.content)
            if match:
                function_name = f'handle_{command["key"]}_search'
                search_function = getattr(self, function_name)
                groups = match.groupdict()
                search_term = groups['search']
                lang = groups['lang']
                await search_function(message, search_term, lang)
                return
        if "[" in message.content:
            await self.handle_team_code(message)

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
                weapon["description"],
                '',
                f'**{weapon["spell_title"]}** {weapon["spell"]["name"]}: {weapon["spell"]["description"]}',
                f'**{weapon["rarity_title"]}** {weapon["rarity"]}',
                f'**{weapon["roles_title"]}** {", ".join(weapon["roles"])}',
                f'**{weapon["type_title"]}** {weapon["type"]}',
            ]
            e.add_field(name=f'{mana} {weapon["name"]}', value='\n'.join(message_lines))

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
                f'**{troop["rarity_title"]}** {troop["rarity"]}',
                f'**{troop["roles_title"]}** {", ".join(troop["roles"])}',
                f'**{troop["type_title"]}** {troop["type"]}',
            ]
            e.add_field(name=f'{mana} {troop["name"]} `#{troop["id"]}`', value='\n'.join(message_lines))
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

    async def handle_team_code(self, message):
        team = self.expander.get_team_from_message(message.content)
        if not team:
            log.debug(f'nothing found in message {message.content}')
            return
        log.debug(f'[{message.guild}][{message.channel}] sending result to {message.author.display_name}: {team}')
        color = discord.Color.from_rgb(19, 227, 246)
        author = message.author.display_name
        author = await pluralize_author(author)
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
        await message.channel.send(embed=e)


if __name__ == '__main__':
    client = DiscordBot()
    client.run(TOKEN)
