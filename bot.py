#!/usr/bin/env python3
import json
import logging
import os
import re
import threading

import discord

from help import get_help_text
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


def debug(message):
    guild = '-'
    if message.guild:
        guild = message.guild.name
    log.debug(f'[{guild}][{message.channel}][{message.author.display_name}] {message.content}')


class DiscordBot(discord.Client):
    DEFAULT_PREFIX = '!'
    PREFIX_CONFIG_FILE = 'prefixes.json'
    BOT_NAME = 'garyatrics.com'
    BASE_GUILD = 'Garyatrics'
    VERSION = '0.3'
    SEARCH_PATTERN = r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.){0} #?(?P<search_term>.*)$'
    COMMAND_REGISTRY = [
        {
            'function': 'handle_troop_search',
            'pattern': re.compile(SEARCH_PATTERN.format('troop'), re.IGNORECASE)
        },
        {
            'function': 'handle_weapon_search',
            'pattern': re.compile(SEARCH_PATTERN.format('weapon'), re.IGNORECASE)
        },
        {
            'function': 'handle_kingdom_search',
            'pattern': re.compile(SEARCH_PATTERN.format('kingdom'), re.IGNORECASE)
        },
        {
            'function': 'handle_pet_search',
            'pattern': re.compile(SEARCH_PATTERN.format('pet'), re.IGNORECASE)
        },
        {
            'function': 'handle_class_search',
            'pattern': re.compile(SEARCH_PATTERN.format('class'), re.IGNORECASE)
        },
        {
            'function': 'handle_talent_search',
            'pattern': re.compile(SEARCH_PATTERN.format('talent'), re.IGNORECASE)
        },
        {
            'function': 'show_help',
            'pattern': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.)help$', re.IGNORECASE)
        },
        {
            'function': 'show_quickhelp',
            'pattern': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.)quickhelp$', re.IGNORECASE)
        },
        {
            'function': 'show_invite_link',
            'pattern': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.)invite$', re.IGNORECASE)
        },
        {
            'function': 'show_prefix',
            'pattern': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.)prefix$', re.IGNORECASE)
        },
        {
            'function': 'change_prefix',
            'pattern': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?(?P<prefix>.)prefix (?P<new_prefix>.+)$',
                                  re.IGNORECASE)
        },
        {
            'function': 'handle_team_code',
            'pattern': re.compile(
                r'.*?(?P<lang>en|fr|de|ru|it|es|cn)?(?P<shortened>-)?\[(?P<team_code>(\d+,?){1,13})\].*',
                re.IGNORECASE)
        }
    ]

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

    async def get_function_for_command(self, user_command, user_prefix):
        for command in self.COMMAND_REGISTRY:
            match = command['pattern'].match(user_command)
            if match:
                groups = match.groupdict()
                if groups.get('prefix', user_prefix) == user_prefix:
                    return getattr(self, command['function']), groups
        return None, None

    async def update_base_emojis(self):
        for guild in self.guilds:
            if guild.name == self.BASE_GUILD:
                for emoji in guild.emojis:
                    self.my_emojis[emoji.name] = str(emoji)

    async def show_help(self, message, prefix, lang):
        help_title, help_text = get_help_text(prefix, lang)

        e = discord.Embed(title=help_title)
        for section, text in help_text.items():
            e.add_field(name=section, value=text, inline=False)
        await message.channel.send(embed=e)

    async def show_quickhelp(self, message, prefix, lang):
        e = discord.Embed(title='quickhelp')
        e.description = (
            f'`{prefix}help` complete help\n'
            f'`{prefix}quickhelp` this command\n'
            f'`{prefix}invite`\n'
            f'`[<troopcode>]` post team\n'
            f'`-[<troopcode>]` post team (short)\n'
            f'`{prefix}troop <search>`\n'
            f'`{prefix}weapon <search>`\n'
            f'`{prefix}pet <search>`\n'
            f'`{prefix}class <search>`\n'
            f'`{prefix}kingdom <search>`\n'
            f'`{prefix}talent <search>`\n'
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

        user_command = message.content.lower().strip()
        my_prefix = self.get_my_prefix(message.guild)
        function, params = await self.get_function_for_command(user_command, my_prefix)
        if function:
            debug(message)
            await function(message, **params)

    async def show_invite_link(self, message, prefix, lang):
        color = discord.Color.from_rgb(255, 255, 255)
        e = discord.Embed(title='Bot invite link', color=color)
        link = 'https://discordapp.com/api/oauth2/authorize?client_id=733399051797790810&scope=bot&permissions=339008'
        e.add_field(name='Feel free to share!', value=link)
        await message.channel.send(embed=e)

    async def change_prefix(self, message, prefix, new_prefix, lang):
        my_prefix = self.get_my_prefix(message.guild)
        issuing_user = message.author
        if not message.guild:
            color = discord.Color.from_rgb(0, 0, 0)
            e = discord.Embed(title='Prefix change', color=color)
            e.add_field(name='Error',
                        value=f'Prefix change not possible in direct messages.')
            await message.channel.send(embed=e)
            return
        guild_owner = message.guild.owner
        if issuing_user == guild_owner:
            if len(new_prefix) != 1:
                color = discord.Color.from_rgb(0, 0, 0)
                e = discord.Embed(title='Prefix change', color=color)
                e.add_field(name='Error',
                            value=f'Your new prefix has to be 1 characters long, `{new_prefix}` has {len(new_prefix)}.')
                await message.channel.send(embed=e)
                return
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

    async def handle_kingdom_search(self, message, search_term, lang, prefix):
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
            e.add_field(name=f'{kingdom["name"]} `#{kingdom["id"]}` ({kingdom["map"]})', value='\n'.join(message_lines))
        else:
            color = discord.Color.from_rgb(255, 255, 255)
            e = discord.Embed(title=f'Class search for `{search_term}` found {len(result)} matches.', color=color)
            kingdoms_found = [f'{kingdom["name"]} `{kingdom["id"]}`' for kingdom in result]
            kingdom_chunks = chunks(kingdoms_found, 30)
            for i, chunk in enumerate(kingdom_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await message.channel.send(embed=e)

    async def handle_class_search(self, message, search_term, lang, prefix):
        result = self.expander.search_class(search_term, lang)
        if not result:
            color = discord.Color.from_rgb(0, 0, 0)
            e = discord.Embed(title='Class search', color=color)
            e.add_field(name=search_term, value='did not yield any result.')
        elif len(result) == 1:
            _class = result[0]
            e = discord.Embed(title='Class search')
            class_lines = [
                f'**{_class["kingdom_title"]}**: {_class["kingdom"]}',
                f'**{_class["weapon_title"]}**: {_class["weapon"]}',
                _class['type'],
            ]
            e.add_field(name=f'{_class["name"]} `#{_class["id"]}`', value='\n'.join(class_lines), inline=False)
            trait_list = [f'**{trait["name"]}**: {trait["description"]}' for trait in _class['traits']]
            traits = '\n'.join(trait_list)
            e.add_field(name=_class["traits_title"], value=traits, inline=False)
            for i, tree in enumerate(_class['talents']):
                talents = [f'**{t["name"]}**: ({t["description"]})' for t in tree]
                e.add_field(name=f'__{_class["trees"][i]}__', value='\n'.join(talents), inline=True)
        else:
            color = discord.Color.from_rgb(255, 255, 255)
            e = discord.Embed(title=f'Class search for `{search_term}` found {len(result)} matches.', color=color)
            classes_found = [f'{_class["name"]} ({_class["id"]})' for _class in result]
            class_chunks = chunks(classes_found, 30)
            for i, chunk in enumerate(class_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await message.channel.send(embed=e)

    async def handle_pet_search(self, message, search_term, lang, prefix):
        result = self.expander.search_pet(search_term, lang)
        if not result:
            color = discord.Color.from_rgb(0, 0, 0)
            e = discord.Embed(title='Pet search', color=color)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            pet = result[0]
            e = discord.Embed(title='Pet search')
            mana = self.my_emojis.get(pet['color_code'])
            effect_data = ''
            if pet['effect_data']:
                effect_data = f' ({pet["effect_data"]})'
            message_lines = [
                f'**{pet["effect_title"]}**: {pet["effect"]}{effect_data}',
                f'**{pet["kingdom_title"]}**: {pet["kingdom"]}',
            ]
            e.add_field(name=f'{mana} {pet["name"]} `#{pet["id"]}`', value='\n'.join(message_lines))
        else:
            color = discord.Color.from_rgb(255, 255, 255)
            e = discord.Embed(title=f'Pet search for `{search_term}` found {len(result)} matches.', color=color)
            pets_found = [f'{pet["name"]} ({pet["id"]})' for pet in result]
            pet_chunks = chunks(pets_found, 30)
            for i, chunk in enumerate(pet_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await message.channel.send(embed=e)

    async def handle_weapon_search(self, message, search_term, lang, prefix):
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
            color_requirement = []
            if weapon['requirement'] < 1000:
                color_requirement = [f'{self.my_emojis.get(c, f":{c}:")}' for c in weapon['colors']]
            affixes = '\n'.join([f'**{affix["name"]}**: {affix["description"]}' for affix in weapon['affixes']])
            affix_text = ''
            if weapon['affixes']:
                affix_text = f'\n**{weapon["affix_title"]}**\n{affixes}\n'
            message_lines = [
                weapon['spell']['description'],
                '',
                f'**{weapon["kingdom_title"]}**: {weapon["kingdom"]}',
                f'**{weapon["rarity_title"]}**: {weapon["rarity"]}',
                f'**{weapon["roles_title"]}**: {", ".join(weapon["roles"])}',
                f'**{weapon["type_title"]}**: {weapon["type"]}',
                affix_text,
                f'{weapon["requirement_text"].replace("erhähltlich", "erhältlich")} {" ".join(color_requirement)}',
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

    async def handle_troop_search(self, message, prefix, search_term, lang):
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

    async def handle_talent_search(self, message, search_term, lang, prefix):
        result = self.expander.search_talent_tree(search_term, lang)
        if not result:
            color = discord.Color.from_rgb(0, 0, 0)
            e = discord.Embed(title='Talent search', color=color)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            tree = result[0]
            e = discord.Embed(title='Talent search')
            talents = [f'**{t["name"]}**: ({t["description"]})' for t in tree['talents']]
            e.add_field(name=f'__{tree["name"]}__', value='\n'.join(talents), inline=True)
            e.add_field(name='__Classes using this Talent Tree:__', value=', '.join(tree['classes']), inline=False)
        else:
            color = discord.Color.from_rgb(255, 255, 255)
            e = discord.Embed(title=f'Talent search for `{search_term}` found {len(result)} matches.', color=color)
            talent_found = []
            for t in result:
                talents_matches = f'({", ".join(t["talent_matches"])})' if 'talent_matches' in t else ''
                talent_found.append(f'{t["name"]} {talents_matches}')
            troop_chunks = chunks(talent_found, 30)
            for i, chunk in enumerate(troop_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await message.channel.send(embed=e)

    async def handle_team_code(self, message, lang, team_code, shortened=''):
        team = self.expander.get_team_from_message(team_code, lang)
        if not team or not team['troops']:
            log.debug(f'nothing found in message {team_code}')
            return
        color = discord.Color.from_rgb(19, 227, 246)
        author = message.author.display_name
        author = await pluralize_author(author)

        if shortened:
            e = self.format_output_team_shortend(team, color)
        else:
            e = self.format_output_team(team, color, author)

        try:
            await message.channel.send(embed=e)
        except discord.errors.Forbidden:
            log.warning(
                f'[{message.guild.name}][{message.channel}] Could not post response, channel is forbidden for me.')

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

    async def show_prefix(self, message, lang, prefix):
        color = discord.Color.from_rgb(255, 255, 255)
        e = discord.Embed(title='Prefix', color=color)
        e.add_field(name='The current prefix is', value=f'`{prefix}`')
        await message.channel.send(embed=e)


if __name__ == '__main__':
    client = DiscordBot()
    client.run(TOKEN)
