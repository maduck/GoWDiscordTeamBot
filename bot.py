#!/usr/bin/env python3
import asyncio
import json
import operator
import os
import random
import re

import discord
from discord.ext import tasks

from base_bot import BaseBot, log
from game_constants import RARITY_COLORS
from help import get_help_text, get_tower_help_text
from jobs.news_downloader import NewsDownloader
from language import Language
from prefix import Prefix
from subscriptions import Subscriptions
from team_expando import TeamExpander
from tower_data import TowerOfDoomData
from translations import Translations
from util import bool_to_emoticon

TOKEN = os.getenv('DISCORD_TOKEN')


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


class DiscordBot(BaseBot):
    DEFAULT_PREFIX = '!'
    DEFAULT_LANGUAGE = 'en'
    BOT_NAME = 'garyatrics.com'
    BASE_GUILD = "Garyatrics"
    VERSION = '0.7'
    GRAPHICS_URL = 'https://garyatrics.com/gow_assets'
    NEEDED_PERMISSIONS = [
        'add_reactions',
        'read_messages',
        'send_messages',
        'embed_links',
        'attach_files',
        'external_emojis',
    ]
    LANG_PATTERN = r'(?P<lang>en|fr|de|ру|ru|it|es|cn)?'
    SEARCH_PATTERN = r'^' + LANG_PATTERN + '(?P<shortened>-)?(?P<prefix>.){0} #?(?P<search_term>.*)$'
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
            'pattern': re.compile(SEARCH_PATTERN.format('pet'), re.IGNORECASE | re.MULTILINE)
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
            'function': 'show_spoilers',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)spoilers?( '
                                                        r'(?P<filter>(weapon|pet|kingdom|troop))s?)?', re.IGNORECASE)
        },
        {
            'function': 'show_events',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)events?$', re.IGNORECASE)
        },
        {
            'function': 'show_help',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)help$', re.IGNORECASE)
        },
        {
            'function': 'show_quickhelp',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)quickhelp$', re.IGNORECASE)
        },
        {
            'function': 'show_invite_link',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)invite$', re.IGNORECASE)
        },
        {
            'function': 'show_prefix',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)prefix$', re.IGNORECASE)
        },
        {
            'function': 'change_prefix',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)prefix (?P<new_prefix>.+)$', re.IGNORECASE)
        },
        {
            'function': 'show_tower_help',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)towerhelp$', re.IGNORECASE)
        },
        {
            'function': 'show_tower_config',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)towerconfig$', re.IGNORECASE)
        },
        {
            'function': 'set_tower_config_alias',
            'pattern': re.compile(
                r'^' + LANG_PATTERN + r'(?P<prefix>.)towerconfig (?P<category>[^ ]+) (?P<field>[^ ]+) (?P<values>.+)$',
                re.IGNORECASE)
        },
        {
            'function': 'set_tower_config_option',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)towerconfig (?P<option>[^ ]+) (?P<value>.+)$',
                                  re.IGNORECASE)
        },
        {
            'function': 'show_tower_data',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)tower$', re.IGNORECASE)
        },
        {
            'function': 'clear_tower_data',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)towerclear$', re.IGNORECASE)
        },
        {
            'function': 'edit_tower_single',
            'pattern': re.compile(
                r'^' + LANG_PATTERN + r'(?P<prefix>.)tower (?P<floor>[^ ]+) (?P<room>[^ ]+) (?P<scroll>[^ ]+)$',
                re.IGNORECASE)
        },
        {
            'function': 'edit_tower_floor',
            'pattern': re.compile(
                r'^' + LANG_PATTERN + r'(?P<prefix>.)tower (?P<floor>[^ ]+) (?P<scroll_ii>[^ ]+) (?P<scroll_iii>[^ ]+) '
                                      r'(?P<scroll_iv>[^ ]+) (?P<scroll_v>[^ ]+) ?(?P<scroll_vi>[^ ]+)?$',
                re.IGNORECASE)
        },
        {
            'function': 'handle_team_code',
            'pattern': re.compile(
                r'.*?' + LANG_PATTERN + r'(?P<shortened>-)?\[(?P<team_code>(\d+,?){1,13})\].*',
                re.IGNORECASE | re.DOTALL)
        },
        {
            'function': 'news_subscribe',
            'pattern': re.compile(r'^(?P<prefix>.)news subscribe$')
        },
        {
            'function': 'news_unsubscribe',
            'pattern': re.compile(r'^(?P<prefix>.)news unsubscribe$')
        },
        {
            'function': 'news_status',
            'pattern': re.compile(r'^(?P<prefix>.)news( status)?$')
        },
        {
            'function': 'waffles',
            'pattern': re.compile(r'^(?P<prefix>.)waffles$')
        },
        {
            'function': 'show_languages',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)lang(uages?)?$', re.IGNORECASE)
        },
        {
            'function': 'change_language',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)lang(uages?)? (?P<new_language>.+)$',
                                  re.IGNORECASE)
        },
        {
            'function': 'show_campaign_tasks',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)campaign( (?P<tier>bronze|silver|gold))?$',
                                  re.IGNORECASE)
        }
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        log.debug(f'--------------------------- Starting {self.BOT_NAME} v{self.VERSION} --------------------------')

        self.expander = TeamExpander()
        self.tower_data = TowerOfDoomData()
        self.prefix = Prefix(self.DEFAULT_PREFIX)
        self.language = Language(self.DEFAULT_LANGUAGE)
        self.subscriptions = Subscriptions()

    async def on_ready(self):
        self.invite_url = f'https://discordapp.com/api/oauth2/authorize' \
                          f'?client_id={self.user.id}' \
                          f'&scope=bot' \
                          f'&permissions={self.permissions.value}'
        log.info(f'Logged in as {self.user.name}')
        log.info(f'Invite with: {self.invite_url}')

        subscriptions = sum([s.get('pc', True) for s in self.subscriptions])
        log.info(f'{subscriptions} channels subscribed to news.')
        guilds = [g.name for g in self.guilds if g]
        log.info(f'Active in {len(guilds)} guilds: {", ".join(guilds)}')

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

    async def show_campaign_tasks(self, message, prefix, lang, tier):
        task_categories = self.expander.get_campaign_tasks(lang)
        e = discord.Embed(title='Campaign Tasks', color=self.WHITE)

        for category, tasks in task_categories.items():
            if tier and category.lower() != tier.lower():
                continue
            category_lines = []
            for task in tasks:
                task_name = task["name"].replace('{Value1}', '`?`')
                category_lines.append(f'**{task["title"]}**: {task_name}')
            e.add_field(name=f'__**{category}**__', value='\n'.join(category_lines), inline=False)
        e.add_field(name='`?`', value='will be set by the game\'s progress.')
        await self.answer(message, e)

    async def show_spoilers(self, message, prefix, lang, filter):
        spoilers = self.expander.get_spoilers(lang)
        e = discord.Embed(title='Spoilers', color=self.WHITE)
        troop_title = self.expander.translate_categories(['troop'], lang)['troop']
        headers = ['Date', 'Rarity', 'Name (ID)']
        if not filter or filter.lower() == 'troop':
            troop_spoilers = [s for s in spoilers if s['type'] == 'troop']

            extra_spacing = 2
            rarity_width = max([len(t['rarity']) for t in troop_spoilers]) + extra_spacing
            header_widths = [12, rarity_width, 5]
            header = ''.join([f'{h.ljust(header_widths[i])}' for i, h in enumerate(headers)])
            message_lines = [header]

            for troop in troop_spoilers:
                message_lines.append(f'{troop["date"]}  '
                                     f'{troop["rarity"].ljust(rarity_width)}'
                                     f'{troop["name"]} '
                                     f'({troop["id"]})')

            if len(message_lines) > 1:
                result = '\n'.join(self.trim_text_lines_to_length(message_lines, 1000))
                e.add_field(name=troop_title, value=f'```{result}```', inline=False)

        categories = ('kingdom', 'pet', 'weapon')
        translated = self.expander.translate_categories(categories, lang)

        for spoil_type in [c for c in categories if (not filter or filter.lower() == c)]:
            message_lines = ['Date        Name (ID)']
            for spoiler in spoilers:
                if spoiler['type'] == spoil_type:
                    message_lines.append(f'{spoiler["date"]}  {spoiler["name"]} ({spoiler["id"]})')
            if len(message_lines) > 1:
                result = '\n'.join(self.trim_text_lines_to_length(message_lines, 1000))
                e.add_field(name=translated[spoil_type], value=f'```{result}```', inline=False)
        await self.answer(message, e)

    async def show_events(self, message, prefix, lang):
        events = self.expander.get_events(lang)
        e = discord.Embed(title='Spoilers', color=self.WHITE)
        message_lines = ['```']
        last_event_date = events[0]['start']
        for event in events:
            if event['start'] > last_event_date and event['start'].weekday() == 0:
                message_lines.append('')
            last_event_date = event['start']
            message_lines.append(f'{event["start"].strftime("%b %d")} - '
                                 f'{event["end"].strftime("%b %d")} '
                                 f'{event["type"]}'
                                 f'{":" if event["extra_info"] else ""} '
                                 f'{event["extra_info"]}')
        message_lines = self.trim_text_lines_to_length(message_lines, 900)
        message_lines.append('```')
        e.add_field(name='Upcoming Events', value='\n'.join(message_lines))
        await self.answer(message, e)

    async def show_help(self, message, prefix, lang):
        help_title, help_text = get_help_text(prefix, lang)

        e = discord.Embed(title=help_title, color=self.WHITE)
        for index, element in enumerate(help_text.items()):
            section, text = element
            # get first element and put in the description
            if index == 0:
                e.description = f'**{section}**\n{text}'
            else:
                e.add_field(name=section, value=text, inline=False)
        await self.answer(message, e)

    async def show_tower_help(self, message, prefix, lang):
        help_title, help_text = get_tower_help_text(prefix, lang)

        e = discord.Embed(title=help_title, color=self.WHITE)
        for section, text in help_text.items():
            e.add_field(name=section, value=text, inline=False)
        await self.answer(message, e)

    async def clear_tower_data(self, message, prefix, lang):
        if not message.guild:
            return
        self.tower_data.clear_data(prefix, message.guild, message)

        e = discord.Embed(title="Tower of Doom", color=self.WHITE)
        e.add_field(name="Success", value=f"Cleared tower data for #{message.channel.name}", inline=False)
        await self.answer(message, e)

    async def show_quickhelp(self, message, prefix, lang):
        e = discord.Embed(title='quickhelp', color=self.WHITE)
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
            f'`{prefix}spoilers`\n'
            f'`{prefix}events`\n'
            f'`<language><command>` language support\n\n'
            f'`{prefix}news [[un]subscribe]` Admin command.\n'
            f'`{prefix}prefix [new_prefix]` Admin command.\n'
            f'`{prefix}language [new_language]` Admin command.\n'
        )
        await self.answer(message, e)

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return

        user_command = message.content.lower().strip()
        my_prefix = self.prefix.get(message.guild)
        function, params = await self.get_function_for_command(user_command, my_prefix)
        if function:
            # handle default language
            if 'lang' in params and params['lang'] is None:
                params['lang'] = self.language.get(message.guild)

            debug(message)
            await function(message, **params)

    async def show_invite_link(self, message, prefix, lang):
        e = discord.Embed(title='Bot invite link', color=self.WHITE)
        e.add_field(name='Feel free to share!', value=self.invite_url)
        await self.answer(message, e)

    async def change_prefix(self, message, prefix, new_prefix, lang):
        my_prefix = self.prefix.get(message.guild)
        if not message.guild:
            e = discord.Embed(title='Prefix change', color=self.RED)
            e.add_field(name='Error',
                        value=f'Prefix change not possible in direct messages.')
            await self.answer(message, e)
            return
        if self.is_guild_admin(message):
            if len(new_prefix) != 1:
                e = discord.Embed(title='Prefix change', color=self.RED)
                e.add_field(name='Error',
                            value=f'Your new prefix has to be 1 characters long, `{new_prefix}` has {len(new_prefix)}.')
                await self.answer(message, e)
                return
            self.prefix.set(message.guild, new_prefix)
            e = discord.Embed(title='Administrative action', color=self.RED)
            e.add_field(name='Prefix change', value=f'Prefix was changed from `{my_prefix}` to `{new_prefix}`')
            await self.answer(message, e)
            log.debug(f'[{message.guild.name}] Changed prefix from {my_prefix} to {new_prefix}')
        else:
            e = discord.Embed(title='There was a problem', color=self.RED)
            e.add_field(name='Prefix change', value=f'Only the server owner has permission to change the prefix.')
            await self.answer(message, e)

    async def handle_kingdom_search(self, message, search_term, lang, prefix, shortened):
        result = self.expander.search_kingdom(search_term, lang)
        if not result:
            e = discord.Embed(title='Kingdom search', color=self.BLACK)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            kingdom = result[0]
            e = discord.Embed(title='Kingdom search', color=self.WHITE)
            underworld = 'underworld' if kingdom['underworld'] else ''
            thumbnail_url = f'{self.GRAPHICS_URL}/Maplocations{underworld}_{kingdom["filename"]}_thumb.png'
            e.set_thumbnail(url=thumbnail_url)
            kingdom_troops = ', '.join([f'{troop["name"]} `{troop["id"]}`' for troop in kingdom['troops']])
            colors = [f'{self.my_emojis.get(c, f":{c}:")}' for c in kingdom['colors']]
            banner_colors = self.banner_colors(kingdom['banner'])

            message_lines = [
                kingdom['punchline'],
                kingdom['description'],
                f'**{kingdom["banner_title"]}**: {kingdom["banner"]["name"]} {" ".join(banner_colors)}',
            ]
            if 'primary_color' in kingdom and 'primary_stat' in kingdom:
                primary_mana = self.my_emojis.get(kingdom['primary_color'])
                deed_emoji = self.my_emojis.get(f'deed_{kingdom["primary_color"]}')
                message_lines.extend([
                    f'**{kingdom["color_title"]}**: {primary_mana} / {deed_emoji} {kingdom["deed"]}',
                    f'**{kingdom["stat_title"]}**: {kingdom["primary_stat"]}',
                ])
            message_lines.extend([
                f'\n**{kingdom["linked_map"]}**: {kingdom["linked_kingdom"]}' if kingdom['linked_kingdom'] else '',
                f'**{kingdom["troop_title"]}**: {kingdom_troops}',
            ])
            e.add_field(name=f'{kingdom["name"]} `#{kingdom["id"]}` {"".join(colors)} ({kingdom["map"]})',
                        value='\n'.join(message_lines))
        elif search_term == 'summary':
            result.sort(key=operator.itemgetter('name'))
            name_width = max([len(k['name']) for k in result])
            col_widths = [name_width, 6, 16]
            message_lines = [
                f'{"Name".ljust(col_widths[0])} {"Troops".ljust(col_widths[1])} Linked Faction',
                ' '.join('-' * col for col in col_widths),
            ]
            message_lines.extend([f'{kingdom["name"].ljust(col_widths[0])} '
                                  f'{str(len(kingdom["troops"])).ljust(col_widths[1])} '
                                  f'{kingdom["linked_kingdom"] or "-"}'
                                  for kingdom in result])
            e = await self.generate_embed_from_text(message_lines, 'Kingdoms', 'Summary')
        else:
            e = discord.Embed(title=f'Class search for `{search_term}` found {len(result)} matches.', color=self.WHITE)
            kingdoms_found = [f'{kingdom["name"]} `{kingdom["id"]}`' for kingdom in result]
            kingdom_chunks = chunks(kingdoms_found, 30)
            for i, chunk in enumerate(kingdom_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await self.answer(message, e)

    async def handle_class_search(self, message, search_term, lang, prefix, shortened):
        result = self.expander.search_class(search_term, lang)
        if not result:
            e = discord.Embed(title='Class search', color=self.BLACK)
            e.add_field(name=search_term, value='did not yield any result.')
        elif len(result) == 1:
            _class = result[0]
            e = discord.Embed(title='Class search', color=self.WHITE)
            thumbnail_url = f'{self.GRAPHICS_URL}/Classes_{_class["code"]}_thumb.png'
            e.set_thumbnail(url=thumbnail_url)
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
        elif search_term == 'summary':
            result.sort(key=operator.itemgetter('name'))
            name_width = max([len(c['name']) for c in result])
            type_width = max([len(c['type_short']) for c in result])
            col_widths = [name_width, type_width, 16]
            message_lines = [
                f'{"Name".ljust(col_widths[0])} {"Type".ljust(col_widths[1])} Kingdom',
                ' '.join('-' * col for col in col_widths),
            ]
            message_lines.extend([f'{_class["name"].ljust(col_widths[0])} '
                                  f'{_class["type_short"].ljust(col_widths[1])} '
                                  f'{_class["kingdom"]}'
                                  for _class in result])

            e = await self.generate_embed_from_text(message_lines, 'Classes', 'Summary')
        else:
            e = discord.Embed(title=f'Class search for `{search_term}` found {len(result)} matches.', color=self.WHITE)
            classes_found = [f'{_class["name"]} ({_class["id"]})' for _class in result]
            class_chunks = chunks(classes_found, 30)
            for i, chunk in enumerate(class_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await self.answer(message, e)

    async def handle_pet_search(self, message, search_term, lang, prefix, shortened):
        result = self.expander.search_pet(search_term, lang)
        if not result:
            e = discord.Embed(title='Pet search', color=self.BLACK)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            pet = result[0]
            e = discord.Embed(title='Pet search', color=self.WHITE)
            thumbnail_url = f'{self.GRAPHICS_URL}/Pets/Cards_{pet["filename"]}_thumb.png'
            e.set_thumbnail(url=thumbnail_url)
            mana = self.my_emojis.get(pet['color_code'])
            effect_data = ''
            if pet['effect_data']:
                effect_data = f' ({pet["effect_data"]})'
            message_lines = [
                f'**{pet["effect_title"]}**: {pet["effect"]}{effect_data}',
                f'**{pet["kingdom_title"]}**: {pet["kingdom"]}',
            ]
            if 'release_date' in pet:
                message_lines.extend(['', f'**Release date**:'])
                e.timestamp = pet["release_date"]
            e.add_field(name=f'{mana} {pet["name"]} `#{pet["id"]}`', value='\n'.join(message_lines))
        else:
            e = discord.Embed(title=f'Pet search for `{search_term}` found {len(result)} matches.', color=self.WHITE)
            pets_found = [f'{pet["name"]} ({pet["id"]})' for pet in result]
            pet_chunks = chunks(pets_found, 30)
            for i, chunk in enumerate(pet_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await self.answer(message, e)

    async def handle_weapon_search(self, message, search_term, lang, prefix, shortened):
        result = self.expander.search_weapon(search_term, lang)
        if not result:
            e = discord.Embed(title='Weapon search', color=self.BLACK)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            weapon = result[0]
            rarity_color = RARITY_COLORS.get(weapon['raw_rarity'], RARITY_COLORS['Mythic'])
            color = discord.Color.from_rgb(*rarity_color)
            e = discord.Embed(title='Weapon search', color=color)
            thumbnail_url = f'{self.GRAPHICS_URL}/Spells/Cards_{weapon["spell_id"]}_thumb.png'
            e.set_thumbnail(url=thumbnail_url)
            mana = self.my_emojis.get(weapon['color_code'])
            color_requirement = []
            if weapon['requirement'] < 1000:
                color_requirement = [f'{self.my_emojis.get(c, f":{c}:")}' for c in weapon['colors']]
            upgrades = '\n'.join([f'**{affix["name"]}**: {affix["description"]}' for affix in weapon['upgrades']])
            affix_text = ''
            if weapon['upgrades']:
                affix_text = f'\n**{weapon["upgrade_title"]}**\n{upgrades}\n'

            requirements = weapon["requirement_text"].replace("erhähltlich", "erhältlich")
            if weapon['has_mastery_requirement_color'] and ':' in requirements:
                requirements = '**' + requirements.replace(': ', '**: ')

            message_lines = [
                weapon['spell']['description'],
                '',
                f'**{weapon["kingdom_title"]}**: {weapon["kingdom"]}',
                f'**{weapon["rarity_title"]}**: {weapon["rarity"]}',
                f'**{weapon["roles_title"]}**: {", ".join(weapon["roles"])}',
                f'**{weapon["type_title"]}**: {weapon["type"]}',
                affix_text,
                f'{requirements} {" ".join(color_requirement)}',
            ]
            if 'release_date' in weapon:
                message_lines.extend([f'**Release date**:'])
                e.timestamp = weapon["release_date"]
            e.add_field(name=f'{weapon["spell"]["cost"]}{mana} {weapon["name"]} `#{weapon["id"]}`',
                        value='\n'.join(message_lines))
        else:
            e = discord.Embed(title=f'Weapon search for `{search_term}` found {len(result)} matches.', color=self.WHITE)
            weapons_found = [f'{t["name"]} ({t["id"]})' for t in result]
            weapon_chunks = chunks(weapons_found, 30)
            for i, chunk in enumerate(weapon_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await self.answer(message, e)

    async def handle_troop_search(self, message, prefix, search_term, lang, shortened):
        result = self.expander.search_troop(search_term, lang)
        if not result:
            e = discord.Embed(title='Troop search', color=self.BLACK)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            troop = result[0]
            rarity_color = RARITY_COLORS.get(troop['raw_rarity'], RARITY_COLORS['Mythic'])
            if 'Boss' in troop['raw_types']:
                rarity_color = RARITY_COLORS['Doomed']
            color = discord.Color.from_rgb(*rarity_color)
            mana = self.my_emojis.get(troop['color_code'])
            mana_display = f'{troop["spell"]["cost"]}{mana} '

            e = discord.Embed(title='Troop search', color=color)

            if shortened:
                e.description = f'**{mana_display}{troop["name"]}**'
                attributes = self.get_list(troop["type"], troop["roles"], troop["rarity"], troop["kingdom"])
                e.description += f' ({", ".join(attributes)}) | {troop["spell"]["description"]}'

                trait_list = [f'{trait["name"]}' for trait in troop['traits']]
                e.description += f'\n{", ".join(trait_list)}'
            else:
                thumbnail_url = f'{self.GRAPHICS_URL}/Troops/Cards_{troop["filename"]}_thumb.png'
                e.set_thumbnail(url=thumbnail_url)
                message_lines = [
                    f'**{troop["spell"]["name"]}**: {troop["spell"]["description"]}',
                    '',
                    f'**{troop["kingdom_title"]}**: {troop["kingdom"]}',
                    f'**{troop["rarity_title"]}**: {troop["rarity"]}',
                    f'**{troop["roles_title"]}**: {", ".join(troop["roles"])}',
                    f'**{troop["type_title"]}**: {troop["type"]}',
                ]

                description = ''
                if troop['description']:
                    description = f' **{troop["description"]}**'

                e.description = f'**{mana_display}{troop["name"]}** `#{troop["id"]}`{description}'
                e.description += '\n' + '\n'.join(message_lines)

                trait_list = [f'**{trait["name"]}**: {trait["description"]}' for trait in troop['traits']]
                if 'release_date' in troop:
                    trait_list.extend(['', f'**Release date**:'])
                    e.timestamp = troop["release_date"]
                traits = '\n'.join(trait_list)
                e.add_field(name=troop["traits_title"], value=traits, inline=False)
        else:
            e = discord.Embed(title=f'Troop search for `{search_term}` found {len(result)} matches.', color=self.WHITE)
            troops_found = [f'{t["name"]} ({t["id"]})' for t in result]
            troop_chunks = chunks(troops_found, 30)
            for i, chunk in enumerate(troop_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)

        await self.answer(message, e)

    async def handle_talent_search(self, message, search_term, lang, prefix, shortened):
        result = self.expander.search_talent_tree(search_term, lang)
        if not result:
            e = discord.Embed(title='Talent search', color=self.BLACK)
            e.add_field(name=search_term, value='did not yield any result')
        elif len(result) == 1:
            tree = result[0]
            e = discord.Embed(title='Talent search', color=self.WHITE)
            talents = [f'**{t["name"]}**: ({t["description"]})' for t in tree['talents']]
            e.add_field(name=f'__{tree["name"]}__', value='\n'.join(talents), inline=True)
            classes = [f'{c["name"]} `#{c["id"]}`' for c in tree['classes']]
            e.add_field(name='__Classes using this Talent Tree:__', value=', '.join(classes), inline=False)
        else:
            e = discord.Embed(title=f'Talent search for `{search_term}` found {len(result)} matches.', color=self.WHITE)
            talent_found = []
            for t in result:
                talents_matches = f'({", ".join(t["talent_matches"])})' if 'talent_matches' in t else ''
                talent_found.append(f'{t["name"]} {talents_matches}')
            troop_chunks = chunks(talent_found, 30)
            for i, chunk in enumerate(troop_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await self.answer(message, e)

    async def handle_team_code(self, message, lang, team_code, shortened=''):
        team = self.expander.get_team_from_message(team_code, lang)
        if not team or not team['troops']:
            log.debug(f'nothing found in message {team_code}')
            return
        color = discord.Color.from_rgb(*RARITY_COLORS['Mythic'])
        author = message.author.display_name
        author = await pluralize_author(author)

        if shortened:
            e = self.format_output_team_shortened(team, color)
        else:
            e = self.format_output_team(team, color, author)

        await self.answer(message, e)

    def get_list(self, *args):
        lst = []
        for arg in args:
            if type(arg) == str and arg != '':
                lst.append(arg)
            elif type(arg) == list:
                # use for loop instead of extend to check if the entry has a value
                for entry in arg:
                    if type(arg) == str and entry != '':
                        lst.append(entry)
                    else:
                        lst.append(entry)
        return lst

    def banner_colors(self, banner):
        return [f'{self.my_emojis.get(d[0], f":{d[0]}:")}{abs(d[1]) * f"{d[1]:+d}"[0]}' for d in banner['colors']]

    def format_output_team(self, team, color, author):
        e = discord.Embed(title=f"{author} team", color=color)
        troops = [f'{self.my_emojis.get(t[0], f":{t[0]}:")} {t[1]}' for t in team['troops']]
        team_text = '\n'.join(troops)
        e.add_field(name=team['troops_title'], value=team_text, inline=True)
        if team['banner']:
            banner_url = f'{self.GRAPHICS_URL}/Banners/Banners_{team["banner"]["filename"]}_thumb.png'
            e.set_thumbnail(url=banner_url)
            banner_colors = self.banner_colors(team['banner'])
            e.add_field(name=team['banner']['name'], value='\n'.join(banner_colors), inline=True)
        if team['class']:
            talents = '\n'.join(team['talents'])
            if all([t == '-' for t in team['talents']]):
                talents = '-'
            e.add_field(name=f'{team["class_title"]}: {team["class"]}', value=talents,
                        inline=False)
        return e

    def format_output_team_shortened(self, team, color):
        e = discord.Embed(color=color)
        troops = [f'{t[1]}' for t in team['troops']]
        e.title = ', '.join(troops)
        descriptions = []

        if team['banner']:
            banner_texts = [f'{self.my_emojis.get(d[0], f":{d[0]}:")}{abs(d[1]) * f"{d[1]:+d}"[0]}' for d in
                            team['banner']['colors']]
            banner = '{banner_name} {banner_texts}'.format(
                banner_name=team['banner']['name'],
                banner_texts=' '.join(banner_texts)
            )
            descriptions.append(banner)
        if team['class']:
            descriptions.append(team["class"])
        if team['talents'] and not all([i == '-' for i in team['talents']]):
            descriptions.append(', '.join(team['talents']))
        e.description = '\n'.join(descriptions)
        return e

    async def waffles(self, message, prefix):
        e = discord.Embed(title='Waffles', color=self.WHITE)
        waffle_no = random.randint(0, 66)
        e.add_field(name='random waffle', value=f'number {waffle_no}')
        e.set_image(url=f'https://garyatrics.com/images/waffles/{waffle_no:03d}.jpg')
        await self.answer(message, e)

    async def show_prefix(self, message, lang, prefix):
        e = discord.Embed(title='Prefix', color=self.WHITE)
        e.add_field(name='The current prefix is', value=f'`{prefix}`')
        await self.answer(message, e)

    async def show_tower_config(self, message, lang, prefix):
        e = self.tower_data.format_output_config(prefix=prefix, guild=message.guild, color=self.WHITE)
        await self.answer(message, e)

    async def set_tower_config_option(self, message, lang, prefix, option, value):
        if self.is_guild_admin(message):
            old_value, new_value = self.tower_data.set_option(guild=message.guild, option=option, value=value)

            if old_value is None and new_value is None:
                e = discord.Embed(title='Administrative action', color=self.RED)
                e.add_field(name='Tower change rejected', value=f'Invalid option `{option}` specified.')
                await self.answer(message, e)
                return

            e = discord.Embed(title='Administrative action', color=self.RED)
            e.add_field(name='Tower change accepted',
                        value=f'Option {option} changed from `{old_value}` to `{new_value}`')
            await self.answer(message, e)
        else:
            e = discord.Embed(title='Administrative action', color=self.RED)
            e.add_field(name='Tower change rejected', value=f'Only admins can change config options.')
            await self.answer(message, e)

    async def set_tower_config_alias(self, message, lang, prefix, category, field, values):
        if self.is_guild_admin(message):
            old_values, new_values = self.tower_data.set_alias(guild=message.guild, category=category, field=field,
                                                               values=values)

            e = discord.Embed(title='Administrative action', color=self.RED)
            e.add_field(name='Tower change accepted',
                        value=f'Alias {category}: `{field}` was changed from `{old_values}` to `{new_values}`.')
            await self.answer(message, e)
        else:
            e = discord.Embed(title='Administrative action', color=self.RED)
            e.add_field(name='Tower change rejected', value=f'Only admins can change config options.')
            await self.answer(message, e)

    async def show_tower_data(self, message, lang, prefix):
        if not message.guild:
            return
        e = self.tower_data.format_output(guild=message.guild, channel=message.channel,
                                          color=self.WHITE)
        await self.answer(message, e)

    async def edit_tower_single(self, message, lang, prefix, floor, room, scroll):
        if not message.guild:
            return
        my_data = self.tower_data.get(message.guild)

        short = my_data["short"]

        r = self.tower_data.edit_floor(prefix=prefix, guild=message.guild,
                                       message=message, floor=floor, room=room, scroll=scroll)

        if short:
            # Respond with a reaction.
            await self.react(message, bool_to_emoticon(r[0]))
        else:
            # Respond with an embed.
            e = discord.Embed(title='Tower of Doom', color=self.WHITE)
            e.add_field(name='Success' if r[0] else 'Failure', value=r[1])
            await self.answer(message, e)

    async def edit_tower_floor(self, message, lang, prefix, floor, scroll_ii, scroll_iii, scroll_iv, scroll_v,
                               scroll_vi=None):
        if not message.guild:
            return
        e = discord.Embed(title='Tower of Doom', color=self.WHITE)

        my_data = self.tower_data.get(message.guild)

        short = my_data["short"]

        room_a = self.tower_data.edit_floor(prefix=prefix, guild=message.guild,
                                            message=message, floor=floor, room="II", scroll=scroll_ii)
        room_b = self.tower_data.edit_floor(prefix=prefix, guild=message.guild,
                                            message=message, floor=floor, room="III", scroll=scroll_iii)
        room_c = self.tower_data.edit_floor(prefix=prefix, guild=message.guild,
                                            message=message, floor=floor, room="IV", scroll=scroll_iv)
        room_d = self.tower_data.edit_floor(prefix=prefix, guild=message.guild,
                                            message=message, floor=floor, room="V", scroll=scroll_v)
        # Mythic Room
        if scroll_vi is not None:
            log.info(scroll_vi)
            room_e = self.tower_data.edit_floor(prefix=prefix, guild=message.guild, message=message, floor=floor,
                                                room="VI", scroll=scroll_vi)
        else:
            room_e = (True, '')

        success = all([room_a[0], room_b[0], room_c[0], room_d[0], room_e[0]])

        if short:
            await self.react(message, bool_to_emoticon(success))
        else:
            e = discord.Embed(title='Tower of Doom', color=self.WHITE)
            edit_text = '\n'.join([
                f"{'Success' if room_a[0] else 'Failure'}: {room_a[1]}",
                f"{'Success' if room_b[0] else 'Failure'}: {room_b[1]}",
                f"{'Success' if room_c[0] else 'Failure'}: {room_c[1]}",
                f"{'Success' if room_d[0] else 'Failure'}: {room_d[1]}",
                f"{'Success' if room_e[0] else 'Failure'}: {room_e[1]}" if scroll_vi is not None else ''
            ])

            e.add_field(name='Edit Tower (Floor)', value=edit_text)
            await self.answer(message, e)

    async def news_subscribe(self, message, prefix):
        if not message.guild:
            return
        if not self.is_guild_admin(message):
            e = discord.Embed(title='News management', color=self.RED)
            e.add_field(name='Subscribe',
                        value=f'Only the server owner has permission to change news subscriptions.')
            await self.answer(message, e)
            return

        self.subscriptions.add(message.guild, message.channel)

        e = discord.Embed(title='News management', color=self.WHITE)
        e.add_field(name='Subscribe',
                    value=f'News will now be posted into channel {message.channel.name}.')
        await self.answer(message, e)

    async def news_unsubscribe(self, message, prefix):
        if not message.guild:
            return
        if not self.is_guild_admin(message):
            e = discord.Embed(title='News management', color=self.RED)
            e.add_field(name='Unsubscribe',
                        value=f'Only the server owner has permission to change news subscriptions.')
            await self.answer(message, e)
            return

        self.subscriptions.remove(message.guild, message.channel)

        e = discord.Embed(title='News management', color=self.WHITE)
        e.add_field(name='Unsubscribe',
                    value=f'News will *not* be posted into channel {message.channel.name}.')
        await self.answer(message, e)

    async def news_status(self, message, prefix):
        if not message.guild:
            return

        subscribed = self.subscriptions.is_subscribed(message.guild, message.channel)
        answer_text = f'News will *not* be posted into channel {message.channel.name}.'
        if subscribed:
            answer_text = f'News will be posted into channel {message.channel.name}.'

        e = discord.Embed(title='News management', color=self.WHITE)
        e.add_field(name='Status', value=answer_text)
        await self.answer(message, e)

    async def show_latest_news(self):
        if not self.is_ready():
            return

        with open(NewsDownloader.NEWS_FILENAME) as f:
            articles = json.load(f)
            articles.reverse()
        pc_subscriptions = [s for s in self.subscriptions if s.get('pc', True)]
        if articles:
            log.debug(f'Distributing {len(articles)} news articles to {len(pc_subscriptions)} channels.')
        for article in articles:
            for subscription in pc_subscriptions:
                channel = self.get_channel(subscription['channel_id'])
                e = discord.Embed(title='Gems of War news', color=self.WHITE, url=article['url'])
                log.debug(
                    f'Sending out {article["title"]} to {subscription["guild_name"]}/{subscription["channel_name"]}')
                content = self.trim_news_to_length(article['content'], article['url'])
                e.add_field(name=article['title'], value=content)
                for image_url in article['images']:
                    e.set_image(url=image_url)
                try:
                    await channel.send(embed=e)
                except Exception as e:
                    log.error('Could not send out news, exception follows')
                    log.exception(e)
        with open(NewsDownloader.NEWS_FILENAME, 'w') as f:
            f.write('[]')

    async def change_language(self, message, new_language, prefix, lang):
        my_language = self.language.get(message.guild)
        if not message.guild:
            e = discord.Embed(title='Default Language', color=self.RED)
            e.add_field(name='Error',
                        value=f'Language change not possible in direct messages.')
            await self.answer(message, e)
            return
        if self.is_guild_admin(message):
            if new_language not in Translations.LANGUAGES:
                e = discord.Embed(title='Default Language', color=self.RED)
                e.add_field(name='Error',
                            value=f'`{new_language}` is not a valid language code.')
                available_langs = ', '.join([f'`{lang_code}`' for lang_code in Translations.LANGUAGES])
                e.add_field(name='Available languages', value=available_langs, inline=False)
                await self.answer(message, e)
                return

            self.language.set(message.guild, new_language)
            e = discord.Embed(title='Default Language', color=self.WHITE)
            e.add_field(name=f'Default language for {message.guild}',
                        value=f'Default language was changed from `{my_language}` to `{new_language}`.')
            await self.answer(message, e)
            log.debug(f'[{message.guild.name}] Changed language from {my_language} to {new_language}.')
        else:
            e = discord.Embed(title='Default Language', color=self.RED)
            e.add_field(name=f'Default language for {message.guild}',
                        value='You don\'t have permissions to change the default language on this server.')
            await self.answer(message, e)

    async def show_languages(self, message, lang, prefix):
        e = discord.Embed(title='Default Language', color=self.WHITE)
        e.add_field(name=f'Default language for {message.guild}',
                    value=f'`{self.language.get(message.guild)}`', inline=False)

        available_langs = ', '.join([f'`{lang_code}`' for lang_code in Translations.LANGUAGES])
        e.add_field(name='Available languages', value=available_langs, inline=False)
        await self.answer(message, e)


@tasks.loop(minutes=5, reconnect=False)
async def test_task(discord_client):
    lock = asyncio.Lock()
    async with lock:
        try:
            downloader = NewsDownloader()
            downloader.process_news_feed()
            await discord_client.show_latest_news()
        except Exception as e:
            log.error('Could not update news. Stacktrace follows.')
            log.exception(e)


if __name__ == '__main__':
    client = DiscordBot()
    test_task.start(client)
    if TOKEN is not None:
        client.run(TOKEN)
    else:
        log.error('FATAL ERROR: DISCORD_TOKEN env var was not specified.')
