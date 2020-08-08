#!/usr/bin/env python3
import asyncio
import datetime
import json
import operator
import os
import random
import re

import discord
from discord.ext import tasks

from base_bot import BaseBot, log
from discord_helpers import admin_required, guild_required
from game_constants import RARITY_COLORS
from help import get_help_text, get_tower_help_text
from jobs.news_downloader import NewsDownloader
from language import Language
from prefix import Prefix
from subscriptions import Subscriptions
from team_expando import TeamExpander, update_translations
from tower_data import TowerOfDoomData
from translations import LANG_FILES, Translations
from util import bool_to_emoticon, chunks, pluralize_author
from views import Views

TOKEN = os.getenv('DISCORD_TOKEN')


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
                r'^' + LANG_PATTERN + r'(?P<prefix>.)towerconfig (?P<category>[^ ]+) (?P<field>(rooms|scrolls))'
                                      r' (?P<values>.+)$',
                re.IGNORECASE)
        },
        {
            'function': 'set_tower_config_option',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)towerconfig (?P<option>(short|hide))'
                                                        r' (?P<value>.+)$',
                                  re.IGNORECASE)
        },
        {
            'function': 'reset_tower_config',
            'pattern': re.compile(r'^' + LANG_PATTERN + r'(?P<prefix>.)towerconfig reset$', re.IGNORECASE)
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
        self.views = Views(emojis=None)

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
        self.views.my_emojis = self.my_emojis

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
        e.set_footer(text='`?` will be set by the game\'s progress.')
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
            if 'lang' in params and params['lang'] is None:
                params['lang'] = self.language.get(message.guild)

            debug(message)
            await function(message=message, **params)

    async def show_invite_link(self, message, prefix, lang):
        e = self.generate_response('Bot invite link', self.WHITE, 'Feel free to share!', self.invite_url)
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def change_prefix(self, message, prefix, new_prefix, lang):
        my_prefix = self.prefix.get(message.guild)
        if len(new_prefix) != 1:
            e = self.generate_response('Prefix change', self.RED, 'Error',
                                       f'Your new prefix has to be 1 characters long,'
                                       f' `{new_prefix}` has {len(new_prefix)}.')
            await self.answer(message, e)
            return
        self.prefix.set(message.guild, new_prefix)
        e = self.generate_response('Administrative action', self.RED, 'Prefix change',
                                   f'Prefix was changed from `{my_prefix}` to `{new_prefix}`')
        await self.answer(message, e)
        log.debug(f'[{message.guild.name}] Changed prefix from {my_prefix} to {new_prefix}')

    async def handle_kingdom_search(self, message, search_term, lang, prefix, shortened):
        result = self.expander.search_kingdom(search_term, lang)
        if not result:
            e = self.generate_response('Kingdom search', self.BLACK, search_term, 'did not yield any result')
        elif len(result) == 1:
            kingdom = result[0]
            e = self.views.render_kingdom(kingdom)
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
            e = self.views.render_class(_class)
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
            e = self.views.render_pet(result[0])
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
            e = self.generate_response('Weapon search', self.BLACK, search_term, 'did not yield any result')
        elif len(result) == 1:
            e = self.views.render_weapon(result[0])
        else:
            e = discord.Embed(title=f'Weapon search for `{search_term}` found {len(result)} matches.', color=self.WHITE)
            weapons_found = [f'{t["name"]} ({t["id"]})' for t in result]
            weapon_chunks = chunks(weapons_found, 30)
            for i, chunk in enumerate(weapon_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await self.answer(message, e)

    @staticmethod
    def generate_response(title, color, name, value):
        e = discord.Embed(title=title, color=color)
        e.add_field(name=name, value=value)
        return e

    async def handle_troop_search(self, message, prefix, search_term, lang, shortened):
        result = self.expander.search_troop(search_term, lang)
        if not result:
            e = self.generate_response('Troop search', self.BLACK, search_term, 'did not yield any result')
        elif len(result) == 1:
            troop = result[0]
            e = self.views.render_troop(troop, shortened)
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
            e = self.generate_response('Talent search', self.BLACK, search_term, 'did not yield any result')
        elif len(result) == 1:
            e = self.views.render_talent_tree(result[0])
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
            log.debug(f'nothing found in message {team_code}.')
            return
        color = discord.Color.from_rgb(*RARITY_COLORS['Mythic'])
        author = message.author.display_name
        author = await pluralize_author(author)

        if shortened:
            e = self.views.format_output_team_shortened(team, color)
        else:
            e = self.views.format_output_team(team, color, author)

        await self.answer(message, e)

    async def waffles(self, message, prefix):
        waffle_no = random.randint(0, 66)
        e = self.generate_response('Waffles', self.WHITE, 'random waffle', f'number {waffle_no}')
        e.set_image(url=f'https://garyatrics.com/images/waffles/{waffle_no:03d}.jpg')
        await self.answer(message, e)

    async def show_prefix(self, message, lang, prefix):
        e = self.generate_response('Prefix', self.WHITE, 'The current prefix is', f'`{prefix}`')
        await self.answer(message, e)

    @guild_required
    async def show_tower_config(self, message, lang, prefix):
        e = self.tower_data.format_output_config(prefix=prefix, guild=message.guild, color=self.WHITE)
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def set_tower_config_option(self, message, lang, prefix, option, value):
        old_value, new_value = self.tower_data.set_option(guild=message.guild, option=option, value=value)

        if old_value is None and new_value is None:
            e = self.generate_response('Administrative action', self.RED,
                                       'Tower change rejected', f'Invalid option `{option}` specified.')
            await self.answer(message, e)
            return

        e = self.generate_response('Administrative action', self.RED, 'Tower change accepted',
                                   f'Option {option} changed from `{old_value}` to `{new_value}`')
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def set_tower_config_alias(self, message, lang, prefix, category, field, values):
        old_values, new_values = self.tower_data.set_alias(guild=message.guild, category=category, field=field,
                                                           values=values)

        if old_values is None and new_values is None:
            e = self.generate_response('Administrative action', self.RED, 'Tower change rejected',
                                       f'Invalid data specified.')
            await self.answer(message, e)
            return

        e = self.generate_response('Administrative action', self.RED, 'Tower change accepted',
                                   f'Alias {category}: `{field}` was changed from `{old_values}` to `{new_values}`.')
        await self.answer(message, e)

    @guild_required
    async def show_tower_data(self, message, lang, prefix):
        e = self.tower_data.format_output(guild=message.guild, channel=message.channel,
                                          color=self.WHITE)
        await self.answer(message, e)

    @guild_required
    async def edit_tower_single(self, message, lang, prefix, floor, room, scroll):
        my_data = self.tower_data.get(message.guild)
        short = my_data["short"]
        success, response = self.tower_data.edit_floor(prefix=prefix, guild=message.guild,
                                                       message=message, floor=floor, room=room, scroll=scroll)
        if short:
            await self.react(message, bool_to_emoticon(success))
        else:
            e = self.generate_response('Tower of Doom', self.WHITE, 'Success' if success else 'Failure', response)
            await self.answer(message, e)

    @guild_required
    async def edit_tower_floor(self, message, lang, prefix, floor, scroll_ii, scroll_iii, scroll_iv, scroll_v,
                               scroll_vi=None):

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

    @guild_required
    @admin_required
    async def reset_tower_config(self, message, lang, prefix):
        self.tower_data.reset_config(message.guild)

        e = self.generate_response('Administrative action', self.RED, 'Success', 'Cleared tower config')
        await self.answer(message, e)

    @guild_required
    async def clear_tower_data(self, message, prefix, lang):
        self.tower_data.clear_data(prefix, message.guild, message)

        e = self.generate_response('Tower of Doom', self.WHITE, 'Success',
                                   f'Cleared tower data for #{message.channel.name}')
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def news_subscribe(self, message, prefix):
        self.subscriptions.add(message.guild, message.channel)

        e = self.generate_response('News management', self.WHITE,
                                   'Subscribe', f'News will now be posted into channel {message.channel.name}.')
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def news_unsubscribe(self, message, prefix):
        self.subscriptions.remove(message.guild, message.channel)

        e = self.generate_response('News management', self.WHITE, 'Unsubscribe',
                                   f'News will *not* be posted into channel {message.channel.name}.')
        await self.answer(message, e)

    @guild_required
    async def news_status(self, message, prefix):
        subscribed = self.subscriptions.is_subscribed(message.guild, message.channel)
        answer_text = f'News will *not* be posted into channel {message.channel.name}.'
        if subscribed:
            answer_text = f'News will be posted into channel {message.channel.name}.'

        e = self.generate_response('News management', self.WHITE, 'Status', answer_text)
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

    @guild_required
    @admin_required
    async def change_language(self, message, new_language, prefix, lang):
        my_language = self.language.get(message.guild)
        if new_language not in Translations.LANGUAGES:
            e = discord.Embed(title='Default Language', color=self.RED)
            e.add_field(name='Error',
                        value=f'`{new_language}` is not a valid language code.')
            available_langs = ', '.join([f'`{lang_code}`' for lang_code in Translations.LANGUAGES])
            e.add_field(name='Available languages', value=available_langs, inline=False)
            await self.answer(message, e)
            return

        self.language.set(message.guild, new_language)
        e = self.generate_response('Default Language', self.WHITE, f'Default language for {message.guild}',
                                   f'Default language was changed from `{my_language}` to `{new_language}`.')
        await self.answer(message, e)
        log.debug(f'[{message.guild.name}] Changed language from {my_language} to {new_language}.')

    @guild_required
    async def show_languages(self, message, lang, prefix):
        e = discord.Embed(title='Default Language', color=self.WHITE)
        e.add_field(name=f'Default language for {message.guild}',
                    value=f'`{self.language.get(message.guild)}`', inline=False)

        available_langs = ', '.join([f'`{lang_code}`' for lang_code in Translations.LANGUAGES])
        e.add_field(name='Available languages', value=available_langs, inline=False)
        await self.answer(message, e)


@tasks.loop(minutes=5, reconnect=False)
async def task_check_for_news(discord_client):
    lock = asyncio.Lock()
    async with lock:
        try:
            downloader = NewsDownloader()
            downloader.process_news_feed()
            await discord_client.show_latest_news()
        except Exception as e:
            log.error('Could not update news. Stacktrace follows.')
            log.exception(e)


@tasks.loop(seconds=20, reconnect=False)
async def task_check_for_data_updates(discord_client):
    filenames = LANG_FILES + ['World.json']
    now = datetime.datetime.now()
    modified_files = []
    for filename in filenames:
        modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
        modified = now - modification_time <= datetime.timedelta(seconds=20)
        if modified:
            modified_files.append(filename)
    if modified_files:
        log.debug(f'Game file modification detected, reloading {", ".join(modified_files)}.')
        lock = asyncio.Lock()
        async with lock:
            del discord_client.expander
            discord_client.expander = TeamExpander()
            update_translations()


if __name__ == '__main__':
    client = DiscordBot()
    task_check_for_news.start(client)
    task_check_for_data_updates.start(client)
    if TOKEN is not None:
        client.run(TOKEN)
    else:
        log.error('FATAL ERROR: DISCORD_TOKEN env var was not specified.')
