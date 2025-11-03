#!/usr/bin/env python3
import asyncio
import datetime
import json
import operator
import os
import random
import time
import urllib
from functools import partial, partialmethod
from typing import Optional

import aiohttp
import discord
import humanize
import prettytable

import bot_tasks
import graphic_campaign_preview
import graphic_map
import graphic_soulforge_preview
import models
from base_bot import BaseBot, InteractionResponseType, log
from command_registry import COMMAND_REGISTRY, add_slash_command, get_all_commands, remove_slash_command
from configurations import CONFIG
from discord_wrappers import admin_required, guild_required, owner_required
from game_constants import CAMPAIGN_COLORS, RARITY_COLORS
from jobs.news_downloader import NewsDownloader
from models.ban import Ban
from models.bookmark import BookmarkError
from models.pet_rescue import PetRescue
from models.pet_rescue_config import PetRescueConfig
from models.toplist import ToplistError
from search import TeamExpander, _
from tower_data import TowerOfDoomData
from translations import HumanizeTranslator, LANGUAGES, LANGUAGE_CODE_MAPPING
from util import bool_to_emoticon, chunks, debug, pluralize_author
from views import Views

TOKEN = os.getenv('DISCORD_TOKEN')

TOWER_OF_DOOM = '[TOWEROFDOOM]'
ADMIN_ACTION = 'Administrative action'
THERE_WAS_A_PROBLEM = 'There was a problem'
NEWS_MANAGEMENT = 'News management'
DEFAULT_LANGUAGE = 'Default Language'


class DiscordBot(BaseBot):
    BOT_NAME = 'garyatrics.com'
    VERSION = '0.91.9'
    NEEDED_PERMISSIONS = [
        'add_reactions',
        'read_messages',
        'send_messages',
        'embed_links',
        'attach_files',
        'external_emojis',
        'manage_messages',
        'mention_everyone',
        'read_message_history',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        log.debug(f'--------------------------- Starting {self.BOT_NAME} v{self.VERSION} --------------------------')

        self.expander = TeamExpander()
        self.tower_data = TowerOfDoomData(self.my_emojis)
        self.prefix = models.Prefix(CONFIG.get('default_prefix'))
        self.language = models.Language(CONFIG.get('default_language'))
        self.subscriptions = models.Subscriptions()
        self.views = Views(emojis={})
        self.pet_rescues = []
        self.pet_rescue_config: Optional[PetRescueConfig] = None
        self.server_status_cache = {'last_updated': datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)}
        self.session = None

    async def on_guild_join(self, guild):
        await super().on_guild_join(guild)
        first_writable_channel = self.first_writable_channel(guild)

        if ban := Ban.get(guild.id):
            log.debug(f'Guild {guild} ({guild.id}) was banned by {ban["author_name"]} because: {ban["reason"]}')
            if first_writable_channel:
                try:
                    ban_message = self.views.render_ban_message(ban)
                    await first_writable_channel.send(embed=ban_message)
                except discord.DiscordException:
                    log.debug(f'Could not send ban message to {first_writable_channel}')
            await guild.leave()
            return

        welcome_message = self.views.render_welcome_message()
        if first_writable_channel:
            await first_writable_channel.send(embed=welcome_message)

    async def special_needed(self, message):
        debug(message)
        is_special = message.author.id in CONFIG.get('special_users')
        is_owner = await self.is_owner(message)
        if CONFIG.get('special_users_only') and not is_owner and not is_special:
            log.debug('Interaction forbidden by configuration.')
            return True
        return False

    async def on_slash_command(self, function, options, message):
        await self.refresh_emojis()
        try:
            if 'lang' not in options:
                options['lang'] = self.language.get(message.guild)
            options['lang'] = LANGUAGE_CODE_MAPPING.get(options['lang'], options['lang'])
            options['prefix'] = '/'
            if await self.special_needed(message):
                return

            await function(message=message, **options)
        except discord.HTTPException as e:
            log.debug(f'Could not answer to slash command: {e}')

    async def on_ready(self):
        if not self.bot_connect:
            self.bot_connect = datetime.datetime.now()
            log.debug(f'Connected at {self.bot_connect}.')
        else:
            await self.on_resumed()
        self.invite_url = discord.utils.oauth_url(
            client_id=self.user.id,
            permissions=self.permissions
        )
        subscriptions = sum(s.get('pc', True) for s in self.subscriptions)
        log.info(f'{subscriptions} channels subscribed to PC news.')

        game = discord.Game("Gems of War")
        await self.change_presence(status=discord.Status.online, activity=game)

        await self.update_base_emojis()
        self.views.my_emojis = self.my_emojis
        self.expander.my_emojis = self.my_emojis
        log.info(f'Logged in as {self.user.name}')
        log.info(f'Active in {len(self.guilds)} guilds.')

        self.pet_rescue_config = PetRescueConfig()
        await self.pet_rescue_config.load()
        self.pet_rescues = await PetRescue.load_rescues(self)
        log.debug(f'Loaded {len(self.pet_rescues)} pet rescues after restart.')
        await self.register_slash_commands()

    async def get_function_for_command(self, user_command, user_prefix):
        for command in COMMAND_REGISTRY:
            match = command['pattern'].search(user_command)
            if not match:
                continue
            groups = match.groupdict()

            if groups.get('prefix', user_prefix) == user_prefix:
                return getattr(self, command['function']), groups
        return None, None

    @owner_required
    async def world_map(self, message, lang, location='krystara', **__):
        async with message.channel.typing():
            start = time.time()
            map_data = self.expander.get_map_data(lang, location)
            image_data = graphic_map.render_all(map_data)
            result = discord.File(image_data, 'gow_world_map.png')
            duration = time.time() - start
            log.debug(f'Soulforge generation took {duration:0.2f} seconds.')
            await message.channel.send(file=result)

    # noinspection StrFormat
    @owner_required
    async def campaign_preview(self, message, lang, switch=None, team_code=None, **__):
        switch = switch or CONFIG.get('default_news_platform') == 'switch'
        async with message.channel.typing():
            if self.is_interaction(message):
                await self.send_slash_command_result(message,
                                                     response_type=InteractionResponseType.
                                                     CHANNEL_MESSAGE_WITH_SOURCE.value,
                                                     content='Please stand by ...',
                                                     embed=None)
            start = time.time()
            campaign_data = self.expander.get_campaign_tasks(lang)
            campaign_data['switch'] = switch
            campaign_data['task_skip_costs'] = self.expander.task_skip_costs
            campaign_data['team'] = None
            campaign_data['week'] = _('[WEEK]', lang).format(self.expander.campaign_week)
            campaign_data['campaign_name'] = _(self.expander.campaign_name, lang)
            if team_code:
                campaign_data['team'] = self.expander.get_team_from_message(team_code, lang)
            image_data = graphic_campaign_preview.render_all(campaign_data)
            result = discord.File(image_data, f'campaign_{lang}_{campaign_data["raw_date"]}.png')
            duration = time.time() - start
            log.debug(f'Campaign generation took {duration:0.2f} seconds.')
            await message.channel.send(file=result)

    @owner_required
    async def soulforge_preview(self, message, lang, search_term, release_date=None, switch=None, **__):
        if switch is None:
            switch = CONFIG.get('default_news_platform') == 'switch'
        async with message.channel.typing():
            if self.is_interaction(message):
                await self.send_slash_command_result(message, content="Image rendering below.", embed=None, file=None,
                                                     response_type=InteractionResponseType.
                                                     DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE)
            start = time.time()
            weapon_data = self.expander.get_soulforge_weapon_image_data(search_term, release_date, switch, lang)
            if not weapon_data:
                e = discord.Embed(title=f'Weapon search for `{search_term}` did not yield any result',
                                  description=':(',
                                  color=self.BLACK)
                return await self.answer(message, e)
            image_data = graphic_soulforge_preview.render_all(weapon_data)
            result = discord.File(image_data, f'soulforge_{release_date}.png')
            duration = time.time() - start
            log.debug(f'Soulforge generation took {duration:0.2f} seconds.')
            await message.channel.send(file=result)
            if self.is_interaction(message):
                await self.delete_slash_command_interaction(message)

    async def render_campaign_lines(self, message, campaign_data, task_skip_costs, lang):
        for category, tasks in campaign_data.items():
            category_lines = [f'**{task["title"]}**: {task["name"].replace("-->", "→")}' for task in tasks]
            color = CAMPAIGN_COLORS.get(category, self.WHITE)
            skip_costs = f'{_("[SKIP_TASK]", lang)}: {task_skip_costs.get(category)} {_("[GEMS]", lang)}'
            e = discord.Embed(title=f'__**{_(category, lang)}**__ ({skip_costs})',
                              description='\n'.join(category_lines), color=color)
            if any('`?`' in line for line in category_lines):
                e.set_footer(text=f'[?]: {_("[IN_PROGRESS]", lang)}')
            await self.answer(message, e, no_interaction=True)

    async def campaign(self, message, lang, tier=None, **__):
        campaign_data = self.expander.get_campaign_tasks(lang, tier)
        task_skip_costs = self.expander.task_skip_costs

        if not campaign_data['has_content']:
            title = _('[NO_CURRENT_TASK]', lang)
            description = _('[CAMPAIGN_COMING_SOON]', lang)
            e = discord.Embed(title=title, description=description, color=self.WHITE)
            return await self.answer(message, e)
        await self.render_campaign_lines(message, campaign_data['campaigns'], task_skip_costs, lang)

    async def reroll_tasks(self, message, lang, tier=None, **__):
        rerolls = self.expander.get_reroll_tasks(lang, tier)
        task_skip_costs = self.expander.task_skip_costs
        await self.render_campaign_lines(message, rerolls, task_skip_costs, lang)

    async def orbs(self, message, lang, **__):
        orbs = self.expander.get_orbs(lang)
        e = self.views.render_orbs(orbs, lang)
        return await self.answer(message, e)

    async def medals(self, message, lang, **__):
        medals = self.expander.get_medals(lang)
        e = self.views.render_medals(medals, lang)
        return await self.answer(message, e)

    async def adventures(self, message, lang, **__):
        adventures = self.expander.get_adventure_board(lang)
        e = self.views.render_adventure_board(adventures, lang)
        return await self.answer(message, e)

    async def effects(self, message, lang, **__):
        effects = self.expander.get_effects(lang)
        e = self.views.render_effects(effects, lang)
        return await self.answer(message, e)

    async def spoilers(self, message, lang, **kwargs):
        _filter = kwargs.get('filter')
        spoilers = self.expander.get_spoilers(lang)
        e = discord.Embed(title='Spoilers', color=self.WHITE)
        troop_title = self.expander.translate_categories(['troop'], lang)['troop']
        headers = [_('[DAY]', lang), _('[RARITY]', lang), 'Name (ID)']
        if not _filter or _filter.lower() == 'troop':
            troop_spoilers = [s for s in spoilers if s['type'] == 'troop']
            extra_spacing = 2
            rarity_width = max(len(t['rarity']) for t in troop_spoilers) + extra_spacing
            header_widths = [12, rarity_width, 5]
            header = ''.join([f'{h.ljust(header_widths[i])}' for i, h in enumerate(headers)])
            message_lines = [header]

            message_lines.extend(f'{troop["date"]}  '
                                 f'{troop["rarity"].ljust(rarity_width)}'
                                 f'{troop["event"]}'
                                 f'{troop["name"]} '
                                 f'({troop["id"]})' for troop in troop_spoilers)
            if len(message_lines) > 1:
                limit = 1024 - len('``````')
                result = self.views.trim_text_to_length('\n'.join(message_lines), limit)
                e.add_field(name=troop_title, value=f'```{result}```', inline=False)

        categories = ('kingdom', 'pet', 'weapon', 'classe')
        translated = self.expander.translate_categories(categories, lang)

        for spoil_type in [c for c in categories if (not _filter or _filter.lower() == c)]:
            message_lines = ['Date        Name (ID)']
            message_lines.extend(
                f'{spoiler["date"]}  {spoiler["name"]} ({spoiler["id"]})'
                for spoiler in spoilers
                if spoiler['type'] == spoil_type
            )

            if len(message_lines) > 1:
                result = '\n'.join(self.views.trim_text_lines_to_length(message_lines, 900))
                e.add_field(name=translated[spoil_type], value=f'```{result}```', inline=False)
        await self.answer(message, e)

    async def soulforge(self, message, lang, **kwargs):
        title, craftable_items = self.expander.get_soulforge(lang)
        e = discord.Embed(title=title, description=_('[WEAPON_AVAILABLE_FROM_SOULFORGE]', lang), color=self.WHITE)

        def time_left(r):
            if r["end"] is None or r["start"] is None:
                return ""
            days = (r["end"] - r["start"]).days
            return f'`{days} {_("[DAYS]", lang)}`'
        for category, recipes in craftable_items.items():
            recipes = sorted(recipes, key=operator.itemgetter('rarity_number', 'id'), reverse=True)
            message_lines = '\n'.join(
                [f'{self.my_emojis.get(r["raw_rarity"])} {r["name"]} {time_left(r)}' for r in recipes])
            e.add_field(name=category, value=message_lines, inline=True)
        await self.answer(message, e)
        if kwargs.get('lengthened'):
            await self.summoning_stones(message, lang, no_interaction=True)

    async def summoning_stones(self, message, lang, no_interaction=False, **__):
        title, stones = self.expander.get_summons(lang)
        e = self.views.render_summoning_stones(title, stones, lang)
        await self.answer(message, e, no_interaction=no_interaction)

    async def about(self, message, lang, prefix, **__):
        color = discord.Color.from_rgb(*RARITY_COLORS['Mythic'])
        e = discord.Embed(title=_('[INFO]', lang), description='<https://garyatrics.com/>', color=color)
        e.set_thumbnail(url=self.user.avatar.url)
        version_title = _('[SETTINGS_VERSION_NO]', lang).replace(':', '')
        e.add_field(name=f'__{version_title}__:', value=self.VERSION, inline=False)

        with HumanizeTranslator(LANGUAGE_CODE_MAPPING.get(lang, lang)) as _t:
            offline = humanize.naturaldelta(self.downtimes)
            start_time = humanize.naturaltime(self.bot_start)
        e.add_field(name=f'__{_("[START]", lang)}__:', value=start_time)
        e.add_field(name=f'__{_("[OFF]", lang)}__:', value=offline)

        bot_runtime = datetime.datetime.now() - self.bot_start
        availability = (bot_runtime - self.downtimes) / bot_runtime
        e.add_field(name=f'__{_("[AVAILABLE]", lang)}__:', value=f'{availability:.3%}')

        slash_invite = self.invite_url.replace('scope=bot', 'scope=applications.commands')
        e.add_field(name=f'__{_("[INVITE]", lang)}__:',
                    value=f'[Bot]({self.invite_url}) / [Slash Commands]({slash_invite})', inline=False)

        admin_invite = self.invite_url.split('permissions')[0] + 'permissions=8'
        admin_slash_invite = admin_invite.replace('scope=bot', 'scope=applications.commands')
        e.add_field(name=f'__{_("[INVITE]", lang)} ({_("[ADMIN]", lang)})__:',
                    value=f'[Bot]({admin_invite}>) / [Slash Commands]({admin_slash_invite})', inline=False)

        e.add_field(name=f'__{_("[HELP]", lang)}__:', value=f'`{prefix}help` / `{prefix}quickhelp`', inline=False)

        e.add_field(name=f'__{_("[SUPPORT]", lang)}__:', value='<https://discord.gg/XWs7x3cFTU>', inline=False)
        github = self.my_emojis.get('github')
        gold = self.my_emojis.get('gold')
        contribute = f'{gold} <https://www.buymeacoffee.com/garyatrics>\n' \
                     f'{github} <https://github.com/maduck/GoWDiscordTeamBot>'
        e.add_field(name=f'__{_("[CONTRIBUTE]", lang)}__:', value=contribute, inline=False)
        await self.answer(message, e)

    @owner_required
    async def stats(self, message, lang, **__):
        color = discord.Color.from_rgb(*RARITY_COLORS['Mythic'])
        e = discord.Embed(title=_('[PVPSTATS]', lang), description='<https://garyatrics.com/>', color=color)
        members = sum(g.member_count for g in self.guilds)

        with HumanizeTranslator(LANGUAGE_CODE_MAPPING.get(lang, lang)) as _t:
            collections = [
                f'**{_("[GUILD]", lang)} {_("[AMOUNT]", lang)}**: {humanize.intcomma(len(self.guilds))}',
                f'**{_("[PLAYER]", lang)} {_("[AMOUNT]", lang)}**: {humanize.intcomma(members)}',
                f'**{_("[NEWS]", lang)} {_("[CHANNELS]", lang)} (PC)**: '
                f'{humanize.intcomma(sum(s.get("pc", True) for s in self.subscriptions))}',
                f'**{_("[NEWS]", lang)} {_("[CHANNELS]", lang)} (Switch)**: '
                f'{humanize.intcomma(sum(s.get("switch", True) for s in self.subscriptions))}',
                f'**{_("[PETRESCUE]", lang)} ({_("[JUST_NOW]", lang)})**: {humanize.intcomma(len(self.pet_rescues))}',
                f'**{_("[PETRESCUE]", lang)} ({_("[TRAIT_ALL]", lang)})**: {humanize.intcomma(PetRescue.get_amount())}',
            ]
            e.add_field(name=_("[COLLECTION]", lang), value='\n'.join(collections))

        await self.answer(message, e)

    async def events(self, message, lang, **kwargs):
        events = self.expander.get_events(lang)
        e = self.views.render_events(events, kwargs.get('filter'), lang)
        await self.answer(message, e)

    async def current_event(self, message, lang, shortened=False, lengthened=False, **__):
        lang = LANGUAGE_CODE_MAPPING.get(lang, lang)
        current_event = self.expander.get_current_event(lang, self.my_emojis)
        e = self.views.render_current_event(current_event, shortened, lengthened, lang)
        for i, field in enumerate(e.fields):
            if len(field.value) >= 1024:
                new_value = f'{field.value[:1020]} ...'
                e.set_field_at(i, name=field.name, value=new_value)
        await self.answer(message, e)

    async def active_gems(self, message, lang, **__):
        gems = self.expander.get_active_gems(lang)
        e = self.views.render_active_gems(gems, lang)
        await self.answer(message, e)

    async def heroic_gems(self, message, lang, **__):
        gems = self.expander.get_heroic_gems(lang)
        e = self.views.render_heroic_gems(gems, lang)
        if len(e.fields) > 25:
            all_fields = e.fields
            e.clear_fields()
            [e.add_field(name=field.name, value=field.value, inline=field.inline) for field in all_fields[:25]]
            await self.answer(message, e)
            e.clear_fields()
            [e.add_field(name=field.name, value=field.value, inline=field.inline) for field in all_fields[25:]]
            await self.answer(message, e)
            return
        await self.answer(message, e)

    async def color_kingdoms(self, message, lang, **__):
        kingdoms = self.expander.get_color_kingdoms(lang)
        e = self.views.render_color_kingdoms(kingdoms, lang)
        await self.answer(message, e)

    async def troop_type_kingdoms(self, message, lang, **__):
        kingdoms = self.expander.get_type_kingdoms(lang)
        e = self.views.render_type_kingdoms(kingdoms, lang)
        await self.answer(message, e)

    async def event_kingdoms(self, message, lang, **__):
        events = self.expander.get_event_kingdoms(lang)
        e = self.views.render_event_kingdoms(events)
        await self.answer(message, e)

    async def levels(self, message, lang, **__):
        levels = self.expander.get_levels(lang)
        e = self.views.render_levels(levels)
        await self.answer(message, e)

    async def help(self, message, lang, prefix, **__):
        lang = LANGUAGE_CODE_MAPPING.get(lang, lang)
        e = self.views.render_help(prefix, lang)
        await self.answer(message, e)

    async def show_tower_help(self, message, prefix, lang, **__):
        e = self.views.render_tower_help(prefix, lang)
        await self.answer(message, e)

    async def quickhelp(self, message, lang, **__):
        prefix = self.prefix.get(message.guild)
        e = self.views.render_quickhelp(prefix, lang, LANGUAGES)
        await self.answer(message, e)

    async def on_message(self, message):
        if message.author.bot:
            return

        await self.wait_until_ready()

        user_command = message.content.strip()
        my_prefix = self.prefix.get(message.guild)
        func, params = await self.get_function_for_command(user_command, my_prefix)
        if not func:
            return

        await self.refresh_emojis()

        params['lang'] = params.get('lang') or self.language.get(message.guild)
        params['lang'] = params['lang'].lower()
        params['lang'] = LANGUAGE_CODE_MAPPING.get(params['lang'], params['lang'])
        if await self.special_needed(message):
            return

        await func(message=message, **params)

    async def refresh_emojis(self):
        if not self.expander.my_emojis:
            log.debug('Emojis vanished from Expander, refreshing.')
            self.expander.my_emojis = self.my_emojis

    @guild_required
    @admin_required
    async def change_prefix(self, message, new_prefix, **__):
        my_prefix = self.prefix.get(message.guild)
        if len(new_prefix) != 1:
            e = self.generate_response('Prefix change', self.RED, 'Error',
                                       f'Your new prefix has to be 1 characters long,'
                                       f' `{new_prefix}` has {len(new_prefix)}.')
            await self.answer(message, e)
            return
        await self.prefix.set(message.guild, new_prefix)
        e = self.generate_response(ADMIN_ACTION, self.RED, 'Prefix change',
                                   f'Prefix was changed from `{my_prefix}` to `{new_prefix}`')
        await self.answer(message, e)
        log.debug(f'[{message.guild.name}] Changed prefix from {my_prefix} to {new_prefix}')

    # noinspection StrFormat
    async def handle_search(self, message, search_term, lang, title, shortened=False, formatter='{0[name]} `#{0[id]}`',
                            **__):
        search_function = getattr(self.expander, f'search_{title.lower()}')
        result = search_function(search_term, lang)
        if not result:
            e = discord.Embed(title=f'{title} search for `{search_term}` did not yield any result',
                              description=':(',
                              color=self.BLACK)
        elif len(result) == 1:
            view = getattr(self.views, f'render_{title.lower()}')
            e = view(result[0], shortened, lang)
        else:
            e = discord.Embed(title=f'{title} search for `{search_term}` found {len(result)} matches.',
                              color=self.WHITE)
            items_found = [formatter.format(item) for item in result]
            chunk_size = 30
            item_chunks = chunks(items_found, chunk_size)
            for i, chunk in enumerate(item_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {chunk_size * i + 1} - {chunk_size * i + len(chunk)}', value=chunk_message)
        await self.answer(message, e)

    class_ = partialmethod(handle_search, title='Class')
    kingdom = partialmethod(handle_search, title='Kingdom')
    faction = partialmethod(handle_search, title='Faction', formatter='{0[color_emojis]} {0[name]}')
    pet = partialmethod(handle_search, title='Pet', formatter='{0.name} `#{0.id}`')
    weapon = partialmethod(handle_search, title='Weapon')
    affix = partialmethod(handle_search, title='Affix',
                          formatter='{0[name]} ({0[num_weapons]} {0[weapons_title]})')
    troop = partialmethod(handle_search, title='Troop')
    name = '{0[name]}'
    trait = partialmethod(handle_search, title='Trait', formatter=name)
    talent = partialmethod(handle_search, title='Talent', formatter=name)
    traitstones = partialmethod(handle_search, title='Traitstone', formatter=name)

    async def talents(self, message, lang, **__):
        talents = self.expander.get_all_talents(lang)
        e = self.views.render_all_talents(talents, lang)
        await self.answer(message, e)

    async def pet_rescue(self, message, search_term, lang, time_left=59, mention='', **__):
        # sourcery skip: aware-datetime-for-utc
        pets = self.expander.pets.search(search_term, lang, name_only=True, released_only=True,
                                         no_starry=True, no_golden=False)
        if len(pets) != 1:
            e = discord.Embed(title=f'Pet search for `{search_term}` yielded {len(pets)} results.',
                              description='Try again with a different search.',
                              color=self.BLACK)
            return await self.answer(message, e)

        if message.guild and not message.channel.permissions_for(message.guild.me).send_messages:
            e = discord.Embed(
                title='Error',
                description='✘ Bot has no permissions to send messages to this channel.',
                colour=self.RED,
            )
            return await self.answer(message, embed=e)
        pet = pets[0]
        events = self.expander.get_events(lang)
        now = datetime.datetime.utcnow()
        pet_events = [e for e in events if e['raw_type'] == '[PETRESCUE]']
        override_time_left = None
        for event in pet_events:
            if event['start_time'] <= now <= event['end_time'] and event['gacha'] == pet.id:
                override_time_left = (event['end_time'] - now) / datetime.timedelta(minutes=1)

        if hasattr(message, 'interaction_token'):
            await self.answer(message, embed=None, content=_('[PETRESCUE]', lang))
            await self.delete_slash_command_interaction(message)
        answer_method = partial(self.answer, no_interaction=True)
        rescue = PetRescue(pet, time_left, message, mention, lang, answer_method, self.pet_rescue_config,
                           override_time_left)
        e = self.views.render_pet_rescue(rescue)
        await rescue.create_or_edit_posts(e)
        await rescue.add(self.pet_rescues)

    pr = pet_rescue

    async def show_pet_rescue_config(self, message, lang, **__):
        config = self.pet_rescue_config.get(message.channel)

        e = self.views.render_pet_rescue_config(config, lang)
        await self.answer(message, e)

    async def pet_rescue_stats(self, message, lang, **__):
        raw_stats = PetRescue.get_stats()
        stats, rescues = self.expander.translate_pet_rescue_stats(raw_stats, lang)
        e = self.views.render_pet_rescue_stats(stats, rescues, lang)
        await self.answer(message, e)

    @admin_required
    async def set_pet_rescue_config(self, message, key, value, lang, **__):
        key = key.lower()
        valid_keys = self.pet_rescue_config.get(message.channel).keys()
        if key not in valid_keys:
            answer = f'Error: `{key}` is not a valid setting for pet rescues.\n' \
                     f'Try one of those: `{"`, `".join(valid_keys)}`'
            e = self.generate_response(_('[PETRESCUE]', lang), self.BLACK, _("[SETTINGS]", lang), answer)
            return await self.answer(message, e)
        guild = message.guild
        channel = message.channel
        on = _('[ON]', lang)
        yes = _('[YES]', lang)
        translated_trues = [on.lower(), yes.lower()]
        await self.pet_rescue_config.update(guild, channel, key, value, translated_trues)
        await self.show_pet_rescue_config(message, lang)

    async def class_summary(self, message, lang, **__):
        result = self.expander.class_summary(lang)

        table = prettytable.PrettyTable()
        table.field_names = [
            _('[NAME_A_Z]', lang),
            _('[FILTER_TROOPTYPE]', lang),
            _('[FILTER_KINGDOMS]', lang)
        ]
        table.align = 'l'
        table.hrules = prettytable.HEADER
        table.vrules = prettytable.NONE
        [table.add_row([_class['name'], _class['type_short'], _class['kingdom']]) for _class in result]

        e = await self.generate_embed_from_text(table.get_string().split('\n'),
                                                _('[CLASS]', lang),
                                                _('[OVERVIEW]', lang))
        await self.answer(message, e)

    async def kingdom_summary(self, message, lang, **__):
        result = self.expander.kingdom_summary(lang)

        table = prettytable.PrettyTable()
        table.field_names = [
            _('[NAME_A_Z]', lang),
            _('[TROOPS]', lang),
            _('[FACTIONS]', lang),
        ]
        table.align = 'l'
        table.hrules = prettytable.HEADER
        table.vrules = prettytable.NONE
        [table.add_row([kingdom['name'], len(kingdom['troops']), kingdom['linked_kingdom'] or '-']) for kingdom in
         result]

        e = await self.generate_embed_from_text(table.get_string().split('\n'),
                                                _('[KINGDOMS]', lang),
                                                _('[OVERVIEW]', lang))
        await self.answer(message, e)

    async def faction_summary(self, message, lang, **__):
        factions = self.expander.faction_summary(lang)
        e = self.views.render_faction_summary(factions, lang)
        await self.answer(message, e)

    @staticmethod
    def generate_response(title, color, name, value):
        e = discord.Embed(title=title, color=color)
        e.add_field(name=name, value=value)
        return e

    async def team_code(self, message, lang, team_code, shortened='', lengthened='', **kwargs):
        raw_team_code = team_code
        if team_code.startswith('+'):
            team_code = team_code[1:]
            lengthened = True
        if team_code.startswith('-'):
            team_code = team_code[1:]
            shortened = True
        if team_code.startswith('['):
            team_code = team_code[1:-1]
        team = self.expander.get_team_from_message(team_code, lang)
        if not team or not team['troops']:
            log.debug(f'nothing found in message {team_code}.')
            if self.is_interaction(message):
                await self.answer(message, embed=None, content=f'Invalid Team Code: `{raw_team_code}`.')
            return
        author = message.author.display_name
        author = await pluralize_author(author)
        if kwargs.get('title') is None and message.id != 0:
            team_code = None
        e = self.views.render_team(team, author, shortened, lengthened, title=kwargs.get('title', '')[:256])
        await self.answer(message, e)
        if team_code:
            await message.channel.send(content=f'[{team_code}]')

    tc = team_code

    # noinspection StrFormat
    async def foodies(self, message, lang, foodie_no, max_foodies, base_url, title, subtitle):
        random_title = _('[SPELLEFFECT_CAUSERANDOM]', lang)
        if foodie_no and str(foodie_no).isdigit() and 0 <= int(foodie_no) <= max_foodies:
            foodie_no = int(foodie_no)
            image_no = f'~~{random_title}~~ #{foodie_no}'
        else:
            foodie_no = random.randrange(max_foodies + 1)
            image_no = f'{random_title} #{foodie_no}'

        e = self.generate_response(title, self.WHITE, subtitle, image_no)
        url = base_url.format(foodie_no)
        e.set_image(url=url)
        await self.answer(message, e)

    async def waffles(self, message, lang, waffle_no=None, **__):
        max_waffles = 71
        title = _('[QUEST9480_OBJ0_MSG]', lang)
        subtitle = _('[HAND_FEED]', lang)
        base_url = 'https://garyatrics.com/images/waffles/{0:03d}.jpg'
        return await self.foodies(message, lang, waffle_no, max_waffles, base_url, title, subtitle)

    async def burgers(self, message, lang, burger_no=None, **__):
        max_burgers = 32
        title = _('[QUEST9002_OBJ1_MSG]', lang)
        subtitle = _('[3000_BATTLE15_NAME]', lang)
        base_url = 'https://garyatrics.com/images/burgers/{0:03d}.jpg'
        return await self.foodies(message, lang, burger_no, max_burgers, base_url, title, subtitle)

    async def memes(self, message, lang, meme_no=None, **__):
        base_url = 'https://garyatrics.com/images/memes'
        async with self.session.get(f'{base_url}/index.txt') as r:
            content = await r.text()
            available_memes = [m for m in content.split('\n') if m]
        random_title = _('[SPELLEFFECT_CAUSERANDOM]', lang)
        if meme_no and 1 <= int(meme_no) <= len(available_memes):
            meme = available_memes[int(meme_no) - 1]
            image_no = f'~~{random_title}~~ meme `#{int(meme_no)}`'
        else:
            meme_no = random.randrange(len(available_memes))
            meme = available_memes[meme_no]
            image_no = f'{random_title} meme `#{meme_no + 1}`'

        title = _('[Troop_K02_07_DESC]', lang)
        subtitle = _(f'[FUNNY_LOAD_TEXT_{random.randrange(20)}]', lang)
        meme = urllib.parse.quote(meme)
        url = f'{base_url}/{meme}'

        e = self.generate_response(title, self.WHITE, subtitle, image_no)
        e.set_image(url=url)
        await self.answer(message, e)

    async def server_status(self, message, **__):
        now = datetime.datetime.now(datetime.timezone.utc)
        if self.server_status_cache['last_updated'] <= now - datetime.timedelta(seconds=30):
            async with message.channel.typing():
                async with self.session.get('https://status.infinityplustwo.net/status_v2.txt') as r:
                    await asyncio.sleep(2)
                    status = await r.json(content_type='text/plain') if r.ok else {'pGameArray': []}
                    self.server_status_cache['status'] = status['pGameArray'][:-1]
                    self.server_status_cache['last_updated'] = now
        e = self.views.render_server_status(self.server_status_cache)
        await self.answer(message, e)

    async def storms(self, message, lang, **__):
        storms = self.expander.get_storms(lang)
        e = self.views.render_storms(storms, lang)
        await self.answer(message, e)

    async def show_prefix(self, message, prefix, **__):
        e = self.generate_response('Prefix', self.WHITE, 'The current prefix is', f'`{prefix}`')
        await self.answer(message, e)

    @guild_required
    async def show_tower_config(self, message, prefix, **__):
        e = self.tower_data.format_output_config(prefix=prefix, guild=message.guild, color=self.WHITE)
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def set_tower_config_option(self, message, option, value, **__):
        old_value, new_value = self.tower_data.set_option(guild=message.guild, option=option, value=value)

        if old_value is None and new_value is None:
            e = self.generate_response(ADMIN_ACTION, self.RED,
                                       'Tower change rejected', f'Invalid option `{option}` specified.')
            await self.answer(message, e)
            return

        e = self.generate_response(ADMIN_ACTION, self.RED, 'Tower change accepted',
                                   f'Option {option} changed from `{old_value}` to `{new_value}`')
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def set_tower_config_alias(self, message, category, field, values, **__):
        old_values, new_values = self.tower_data.set_alias(guild=message.guild, category=category, field=field,
                                                           values=values)

        if old_values is None and new_values is None:
            e = self.generate_response(
                ADMIN_ACTION,
                self.RED,
                'Tower change rejected',
                'Invalid data specified.',
            )

            await self.answer(message, e)
            return

        e = self.generate_response(ADMIN_ACTION, self.RED, 'Tower change accepted',
                                   f'Alias {category}: `{field}` was changed from `{old_values}` to `{new_values}`.')
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def import_tower_from_taran(self, message, map_name, **__):
        if self.is_interaction(message):
            await self.answer(message, embed=None, content="Importing, please wait.")

        e = self.tower_data.download_from_taran(message, map_name,
                                                version=self.VERSION,
                                                token=CONFIG.get('taran_token'))
        await self.answer(message, e, no_interaction=True)
        if self.is_interaction(message):
            await self.delete_slash_command_interaction(message)

    @guild_required
    async def show_tower_data(self, message, **kwargs):
        _range = kwargs.get('range')
        shortened = kwargs.get('shortened')
        e = self.tower_data.format_output(guild=message.guild, channel=message.channel,
                                          color=self.WHITE, prefix=kwargs['prefix'], _range=_range, shortened=shortened)
        await self.answer(message, e)

    @guild_required
    async def edit_tower_single(self, message, floor, room, scroll, lang, **__):
        success, response = self.tower_data.edit_floor(message=message, floor=floor, room=room, scroll=scroll)
        if self.tower_data.get(message.guild)['short']:
            return await self.react(message, bool_to_emoticon(success))

        e = self.generate_response(_(TOWER_OF_DOOM, lang), self.WHITE, 'Success' if success else 'Failure', response)
        await self.answer(message, e)

    @guild_required
    async def edit_tower_floor(self, message, floor, scroll_ii, scroll_iii, scroll_iv, scroll_v, scroll_vi=None,
                               lang=None, **__):

        rooms = ('ii', 'iii', 'iv', 'v', 'vi')
        scrolls = (scroll_ii, scroll_iii, scroll_iv, scroll_v, scroll_vi)

        rooms = [
            self.tower_data.edit_floor(message=message, floor=floor, room=room, scroll=scrolls[room_id])
            for room_id, room in enumerate(rooms)
        ]
        success = all(r[0] for r in rooms)

        if self.tower_data.get(message.guild)['short']:
            return await self.react(message, bool_to_emoticon(success))

        e = discord.Embed(title=_(TOWER_OF_DOOM, lang), color=self.WHITE)
        edit_text = '\n'.join([
            f"{'Success' if room[0] else 'Failure'}: {room[1]}"
            for room in rooms])

        e.add_field(name='Edit Tower (Floor)', value=edit_text)
        await self.answer(message, e)

    async def drop_rates(self, message, lang, **__):
        drop_chances = self.expander.get_drop_chances(lang)
        e = self.views.render_drop_chances(drop_chances, lang)
        await self.answer(message, e)

    async def warbands(self, message, lang, **__):
        warbands = self.expander.get_warbands(lang)
        e = self.views.render_warbands(warbands, lang)
        await self.answer(message, e)

    async def banners(self, message, lang, **__):
        banners = self.expander.get_banners(lang)
        e1, e2 = self.views.render_banners(banners, lang)
        await self.answer(message, e1)
        await self.answer(message, e2, no_interaction=True)

    async def dungeon_altars(self, message, lang, **__):
        boons = self.expander.get_dungeon_altars(lang)
        e = self.views.render_dungeon_features(boons, lang)
        await self.answer(message, e)

    async def dungeon_traps(self, message, lang, **__):
        boons = self.expander.get_dungeon_traps(lang)
        e = self.views.render_dungeon_features(boons, lang)
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def reset_tower_config(self, message, **__):
        self.tower_data.reset_config(message.guild)

        e = self.generate_response(ADMIN_ACTION, self.RED, 'Success', 'Cleared tower config')
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def clear_tower_data(self, message, lang, **__):
        self.tower_data.clear_data(message)
        e = self.generate_response(_(TOWER_OF_DOOM, lang), self.WHITE, 'Success',
                                   f'Cleared tower data for #{message.channel.name}')
        await self.answer(message, e)

    @guild_required
    async def show_permissions(self, message, **__):
        channel_permissions = message.channel.permissions_for(message.guild.me)
        permissions = {}
        for permission in self.NEEDED_PERMISSIONS:
            has_permission = getattr(channel_permissions, permission)
            permissions[permission] = '✅' if has_permission else '❌'
        e = self.views.render_permissions(message.channel, permissions)
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def news_subscribe(self, message, platform, **__):
        if not platform:
            platform = CONFIG.get('default_news_platform')
        await self.subscriptions.add(message.guild, message.channel, platform)

        e = self.generate_response(NEWS_MANAGEMENT, self.WHITE,
                                   f'News for {platform.title()}',
                                   f'Channel {message.channel.name} is now subscribed and will receive future news.')
        await self.answer(message, e)

    async def show_bookmark(self, message, bookmark_id, lang, shortened='', **__):
        bookmark = self.expander.bookmarks.get(bookmark_id)
        if not bookmark:
            e = self.generate_response('Bookmark', self.BLACK, 'Error', f'Bookmark id `{bookmark_id}` does not exist.')
            return await self.answer(message, e)
        title = f'Bookmark `{bookmark_id}` by {bookmark["author_name"]}\n{bookmark["description"]}'
        return await self.team_code(message, lang, bookmark['team_code'], title=title, shortened=shortened)

    async def show_my_bookmarks(self, message, **__):
        bookmarks = self.expander.bookmarks.get_my_bookmarks(message.author.id)
        e = self.views.render_my_bookmarks(bookmarks, message.author.display_name)
        await self.answer(message, e)

    async def create_bookmark(self, message, description, team_code, lang, shortened='', **__):
        try:
            bookmark_id = await self.expander.bookmarks.add(message.author.id, message.author.display_name, description,
                                                            team_code)
            return await self.show_bookmark(message, bookmark_id, lang, shortened)
        except BookmarkError as te:
            e = self.generate_response('Bookmark', self.BLACK, THERE_WAS_A_PROBLEM, str(te))
            await self.answer(message, e)

    async def delete_bookmark(self, message, bookmark_id, **__):
        try:
            await self.expander.bookmarks.remove(message.author.id, bookmark_id)
            e = self.generate_response('Bookmark', self.WHITE, 'Deletion',
                                       f'Bookmark `{bookmark_id}` was successfully deleted.')
        except BookmarkError as te:
            e = self.generate_response('Bookmark', self.BLACK, THERE_WAS_A_PROBLEM, str(te))
        await self.answer(message, e)

    async def show_toplist(self, message, toplist_id, lang, **__):
        toplist = self.expander.translate_toplist(toplist_id, lang)
        e = self.views.render_toplist(toplist)
        await self.answer(message, e)

    async def create_toplist(self, message, description, items, lang, **kwargs):
        try:
            toplist_ids = self.expander.get_toplist_troop_ids(items, lang)
            items = ','.join(toplist_ids)
            toplist = await self.expander.create_toplist(message, description, items, lang,
                                                         update_id=kwargs.get('toplist_id'))
            e = self.views.render_toplist(toplist)
        except ToplistError as te:
            e = self.generate_response('Toplist', self.BLACK, THERE_WAS_A_PROBLEM, str(te))
        await self.answer(message, e)

    update_toplist = create_toplist

    async def append_toplist(self, message, toplist_id, items, lang, **__):
        try:
            toplist_ids = self.expander.get_toplist_troop_ids(items, lang)
            items = ','.join(toplist_ids)
            await self.expander.toplists.append(toplist_id, message.author.id, message.author.display_name, items)
            toplist = self.expander.translate_toplist(toplist_id, lang)
            e = self.views.render_toplist(toplist)
        except ToplistError as te:
            e = self.generate_response('Toplist', self.BLACK, THERE_WAS_A_PROBLEM, str(te))
        await self.answer(message, e)

    async def delete_toplist(self, message, toplist_id, **__):
        try:
            await self.expander.toplists.remove(message.author.id, toplist_id)
            e = self.generate_response('Toplist', self.WHITE, 'Deletion',
                                       f'Toplist `{toplist_id}` was successfully deleted.')
        except ToplistError as te:
            e = self.generate_response('Toplist', self.BLACK, THERE_WAS_A_PROBLEM, str(te))
        await self.answer(message, e)

    async def show_my_toplists(self, message, **__):
        toplists = self.expander.toplists.get_my_toplists(message.author.id)
        e = self.views.render_my_toplists(toplists, message.author.display_name)
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def news_unsubscribe(self, message, **__):
        await self.subscriptions.remove(message.guild, message.channel)

        e = self.generate_response(NEWS_MANAGEMENT, self.WHITE, 'News for all platforms',
                                   f'News will *not* be posted into channel {message.channel.name} anymore.')
        await self.answer(message, e)

    @guild_required
    async def news_status(self, message, **kwargs):
        subscribed = self.subscriptions.is_subscribed(message.guild, message.channel)
        answer_text = f'Channel {message.channel.name} is *not* subscribed to any news, ' \
                      f'try `{kwargs["prefix"]}news subscribe`.'
        if subscribed:
            platforms = ('PC', 'Switch')
            subscribed_platforms = [p for p in platforms if subscribed.get(p.lower())]
            platforms_text = ' and '.join(subscribed_platforms)
            answer_text = f'{platforms_text} news for will be posted into channel {message.channel.name}.'

        e = self.generate_response(NEWS_MANAGEMENT, self.WHITE, 'Status', answer_text)
        await self.answer(message, e)

    async def class_level(self, message, **kwargs):
        def xp_for(level):
            return int(1 / 2 * (level ** 2 + level))

        low, high = sorted([int(kwargs.get('from') or 0), int(kwargs.get('to'))])
        low = max(0, low)
        high = min(100, high)

        xp_required = xp_for(high) - xp_for(low)
        speeds = {
            xp_per_min: str(round(xp_required / (60 * xp_per_min)))
            for xp_per_min in (2, 4, 6)
        }
        lang = kwargs.get('lang', 'en')
        e = self.views.render_class_level(low, high, xp_required, speeds, lang)
        await self.answer(message, e)

    async def show_latest_news(self):
        if not self.is_ready():
            return

        with open(NewsDownloader.NEWS_FILENAME) as f:
            articles = json.load(f)
            articles.reverse()
        if articles:
            log.debug(f'Distributing {len(articles)} news articles to {len(self.subscriptions)} channels.')
        for article in articles:
            await self.send_out_news(article)
        with open(NewsDownloader.NEWS_FILENAME, 'w') as f:
            f.write('[]')

    async def send_out_news(self, article):
        embeds = self.views.render_news(article)
        relevant_subscriptions = [s for s in self.subscriptions if s.get(article['platform'])]
        for i, subscription in enumerate(relevant_subscriptions):
            channel = self.get_channel(subscription['channel_id'])
            if not channel:
                log.debug(f'Subscription {subscription} is broken, skipping.')
                continue
            if not await self.is_writable(channel):
                log.debug(f'Channel "{channel}" is not writable.')
                continue
            log.debug(f'[{i + 1}/{len(relevant_subscriptions)}] Sending [{article["platform"]}] {article["title"]} '
                      f'to {channel.guild.name}/{channel.name}.')
            for e in embeds:
                try:
                    await channel.send(embed=e)
                except discord.DiscordException as ex:
                    log.error(f'Could not send out news to "{channel}", exception follows')
                    log.exception(ex)

    @guild_required
    @admin_required
    async def change_language(self, message, new_language, **__):
        my_language = self.language.get(message.guild)
        if new_language not in LANGUAGES:
            e = discord.Embed(title=DEFAULT_LANGUAGE, color=self.BLACK)
            e.add_field(name='Error',
                        value=f'`{new_language}` is not a valid language code.')
            self.add_available_languages(e)
            await self.answer(message, e)
            return

        await self.language.set(message.guild, new_language)
        e = self.generate_response(DEFAULT_LANGUAGE, self.WHITE, f'Default language for {message.guild}',
                                   f'Default language was changed from `{my_language}` to `{new_language}`.')
        await self.answer(message, e)
        log.debug(f'[{message.guild.name}] Changed language from {my_language} to {new_language}.')

    @guild_required
    async def show_languages(self, message, **__):
        e = discord.Embed(title=DEFAULT_LANGUAGE, color=self.WHITE)
        e.add_field(name=f'Default language for {message.guild}',
                    value=f'`{self.language.get(message.guild)}`', inline=False)

        self.add_available_languages(e)
        await self.answer(message, e)

    async def tools(self, message, **__):
        e = self.views.render_tools()
        await self.answer(message, e)

    async def communities(self, **kwargs):
        e = self.views.render_communities()
        await self.answer(kwargs['message'], e)

    @staticmethod
    def add_available_languages(e):
        available_langs = ', '.join([f'`{lang_code}`' for lang_code in LANGUAGES])
        e.add_field(name='Available languages', value=available_langs, inline=False)

    @owner_required
    async def search_guild(self, message, search_term, **__):
        matching_guilds = [
            guild
            for guild in self.guilds
            if search_term.lower() in guild.name.lower()
        ]

        e = self.views.render_guilds(matching_guilds)
        await self.answer(message, e)

    @owner_required
    async def kick_guild(self, message, guild_id, **__):
        guild_id = int(guild_id)
        guild = discord.utils.find(lambda g: g.id == guild_id, self.guilds)
        e = self.generate_response('Guild management', self.RED, 'Kick', 'Could not find a guild with that id.')
        if guild:
            await guild.leave()
            e = self.generate_response('Guild management', self.RED, 'Kick', f'Left guild {guild.name}')
        await self.answer(message, e)

    @owner_required
    async def ban_guild(self, message, guild_id, reason, **__):
        Ban.add(int(guild_id), reason, message.author.display_name)
        await self.kick_guild(message=message, guild_id=guild_id)

    async def weekly_summary(self, message, lang, **__):
        summary = self.expander.get_weekly_summary(lang, self.my_emojis)
        e = self.views.render_weekly_summary(summary, lang)
        await self.answer(message, e)

    async def streamers(self, message, **__):
        e = self.views.render_streamers()
        await self.answer(message, e)

    async def hoard_potions(self, message, lang, **__):
        potions = self.expander.get_hoard_potions(lang)
        e = self.views.render_hoard_potions(potions, lang)
        await self.answer(message, e)

    @staticmethod
    def options_changed(theirs, mine):
        if theirs == mine:
            return False
        if not theirs or not mine:
            return True
        if len(theirs) != len(mine):
            return True
        their_options = theirs[0]
        my_options = mine[0]
        if 'required' in my_options and not my_options['required']:
            their_options['required'] = False
        if 'choices' in my_options and not my_options['choices']:
            their_options['choices'] = []
        if options_diff := set(their_options) ^ set(my_options):
            return options_diff
        return False

    @classmethod
    def command_changed(cls, command):
        my_commands = {c['function']: c for c in COMMAND_REGISTRY}
        if command['name'] not in my_commands:
            return True
        my_command = my_commands[command['name']]
        if command.get('description') != my_command.get('description'):
            log.debug(f'Command description changed: {command["name"]}: {command.get("description")!r} vs '
                      f'{my_command.get("description")!r}')
            return True
        if diff := cls.options_changed(command.get('options'), my_command.get('options')):
            log.debug(f'Command options changed: {command["name"]}: {diff!r}')
            return True
        return False

    async def register_slash_commands(self):
        guild_id = CONFIG.get('slash_command_guild_id')
        existing_commands = await get_all_commands(self.user.id, TOKEN, guild_id=guild_id)
        re_register_commands = []
        for command in existing_commands:
            if self.command_changed(command) or CONFIG.get('deregister_slash_commands'):
                log.debug(f'Deregistering slash command {command["name"]}...')
                re_register_commands.append(command['name'])
                await remove_slash_command(self.user.id, TOKEN, guild_id, command['id'])
        if not CONFIG.get('register_slash_commands'):
            return
        for command in COMMAND_REGISTRY:
            if 'description' not in command:
                continue
            if command['function'] in [c['name'] for c in existing_commands] \
                    and command['function'] not in re_register_commands:
                continue
            log.debug(f'Registering slash command {command["function"]}...')
            await add_slash_command(self.user.id,
                                    bot_token=TOKEN,
                                    guild_id=guild_id,
                                    cmd_name=command['function'],
                                    description=command['description'],
                                    options=command.get('options', []))

    task_check_for_news = bot_tasks.task_check_for_news
    task_check_for_data_updates = bot_tasks.task_check_for_data_updates
    task_update_pet_rescues = bot_tasks.task_update_pet_rescues
    task_update_status = bot_tasks.task_report_status

    async def setup_hook(self):
        self.task_check_for_news.start()
        self.task_check_for_data_updates.start()
        self.task_update_pet_rescues.start()
        self.task_update_status.start()
        self.session = aiohttp.ClientSession()


if __name__ == '__main__':
    intents = discord.Intents.default()
    intents.guilds = True
    intents.emojis = True
    intents.messages = True
    intents.reactions = True
    intents.message_content = CONFIG.get('request_messages_content_intent', False)
    client = DiscordBot(intents=intents)

    if TOKEN is not None:
        client.run(TOKEN)
    else:
        log.error('FATAL ERROR: DISCORD_TOKEN env var was not specified.')
