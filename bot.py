#!/usr/bin/env python3
import datetime
import json
import operator
import os
import random
from functools import partialmethod

import discord
import humanize
import prettytable

import bot_tasks
import models
from base_bot import BaseBot, log
from command_registry import COMMAND_REGISTRY, add_slash_command, get_all_commands, remove_slash_command
from configurations import CONFIG
from discord_wrappers import admin_required, guild_required, owner_required
from game_constants import CAMPAIGN_COLORS, RARITY_COLORS, TASK_SKIP_COSTS
from jobs.news_downloader import NewsDownloader
from models.pet_rescue import PetRescue
from models.pet_rescue_config import PetRescueConfig
from models.toplist import ToplistError
from search import TeamExpander, _
from tower_data import TowerOfDoomData
from translations import HumanizeTranslator, LANGUAGES, LANGUAGE_CODE_MAPPING
from util import bool_to_emoticon, chunks, debug, pluralize_author
from views import Views

TOKEN = os.getenv('DISCORD_TOKEN')


class DiscordBot(BaseBot):
    BOT_NAME = 'garyatrics.com'
    VERSION = '0.36.1'
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
        self.pet_rescue_config: PetRescueConfig = None

    async def on_slash_command(self, function, options, message):
        try:
            if 'lang' not in options:
                options['lang'] = self.language.get(message.guild)
            debug(message)
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
        subscriptions = sum([s.get('pc', True) for s in self.subscriptions])
        log.info(f'{subscriptions} channels subscribed to PC news.')

        game = discord.Game("Gems of War")
        await self.change_presence(status=discord.Status.online, activity=game)

        await self.update_base_emojis()
        self.views.my_emojis = self.my_emojis

        self.pet_rescue_config = PetRescueConfig()
        await self.pet_rescue_config.load()
        self.pet_rescues = await PetRescue.load_rescues(self)
        log.debug(f'Loaded {len(self.pet_rescues)} pet rescues after restart.')
        await self.register_slash_commands()
        log.info(f'Logged in as {self.user.name}')
        log.info(f'Active in {len(self.guilds)} guilds.')

    async def get_function_for_command(self, user_command, user_prefix):
        for command in COMMAND_REGISTRY:
            match = command['pattern'].search(user_command)
            if not match:
                continue
            groups = match.groupdict()

            if groups.get('prefix', user_prefix) == user_prefix:
                return getattr(self, command['function']), groups
        return None, None

    async def campaign(self, message, lang, tier=None, **kwargs):
        campaign_data = self.expander.get_campaign_tasks(lang, tier)
        if not campaign_data['has_content']:
            title = _('[NO_CURRENT_TASK]', lang)
            description = _('[CAMPAIGN_COMING_SOON]', lang)
            e = discord.Embed(title=title, description=description, color=self.WHITE)
            return await self.answer(message, e)

        for category, tasks in campaign_data['campaigns'].items():
            category_lines = [f'**{task["title"]}**: {task["name"]}' for task in tasks]
            color = CAMPAIGN_COLORS.get(category, self.WHITE)
            skip_costs = f'{_("[SKIP_TASK]", lang)}: {TASK_SKIP_COSTS.get(category)} {_("[GEMS]", lang)}'
            e = discord.Embed(title=f'__**{_(category, lang)}**__ ({skip_costs})',
                              description='\n'.join(category_lines), color=color)
            e.set_footer(text=f'[?]: {_("[IN_PROGRESS]", lang)}')
            await self.answer(message, e)

    async def adventures(self, message, lang, **kwargs):
        adventures = self.expander.get_adventure_board(lang)
        e = self.views.render_adventure_board(adventures, lang)
        return await self.answer(message, e)

    async def spoilers(self, message, lang, **kwargs):
        _filter = kwargs.get('filter')
        spoilers = self.expander.get_spoilers(lang)
        e = discord.Embed(title='Spoilers', color=self.WHITE)
        troop_title = self.expander.translate_categories(['troop'], lang)['troop']
        headers = ['Date', 'Rarity', 'Name (ID)']
        if not _filter or _filter.lower() == 'troop':
            troop_spoilers = [s for s in spoilers if s['type'] == 'troop']
            extra_spacing = 2
            rarity_width = max([len(t['rarity']) for t in troop_spoilers]) + extra_spacing
            header_widths = [12, rarity_width, 5]
            header = ''.join([f'{h.ljust(header_widths[i])}' for i, h in enumerate(headers)])
            message_lines = [header]

            for troop in troop_spoilers:
                message_lines.append(f'{troop["date"]}  '
                                     f'{troop["rarity"].ljust(rarity_width)}'
                                     f'{troop["event"]}'
                                     f'{troop["name"]} '
                                     f'({troop["id"]})')

            if len(message_lines) > 1:
                limit = 1024 - len('``````')
                result = self.views.trim_text_to_length('\n'.join(message_lines), limit)
                e.add_field(name=troop_title, value=f'```{result}```', inline=False)

        categories = ('kingdom', 'pet', 'weapon')
        translated = self.expander.translate_categories(categories, lang)

        for spoil_type in [c for c in categories if (not _filter or _filter.lower() == c)]:
            message_lines = ['Date        Name (ID)']
            for spoiler in spoilers:
                if spoiler['type'] == spoil_type:
                    message_lines.append(f'{spoiler["date"]}  {spoiler["name"]} ({spoiler["id"]})')
            if len(message_lines) > 1:
                result = '\n'.join(self.views.trim_text_lines_to_length(message_lines, 900))
                e.add_field(name=translated[spoil_type], value=f'```{result}```', inline=False)
        await self.answer(message, e)

    async def soulforge(self, message, lang, **kwargs):
        title, craftable_items = self.expander.get_soulforge(lang)
        e = discord.Embed(title=title, color=self.WHITE)
        for category, recipes in craftable_items.items():
            recipes = sorted(recipes, key=operator.itemgetter('rarity', 'id'))
            message_lines = '\n'.join([f'{r["name"]} `{r["id"]}`' for r in recipes])
            e.add_field(name=category, value=message_lines, inline=False)
        await self.answer(message, e)

    async def about(self, message, lang, **kwargs):
        color = discord.Color.from_rgb(*RARITY_COLORS['Mythic'])
        e = discord.Embed(title=_('[INFO]', lang), description='<https://garyatrics.com/>', color=color)
        e.set_thumbnail(url=self.user.avatar_url)
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

        my_prefix = self.prefix.get(message.guild)
        e.add_field(name=f'__{_("[HELP]", lang)}__:', value=f'`{my_prefix}help` / `{my_prefix}quickhelp`', inline=False)

        e.add_field(name=f'__{_("[SUPPORT]", lang)}__:', value='<https://discord.gg/XWs7x3cFTU>', inline=False)
        e.add_field(name=f'__{_("[CONTRIBUTE]", lang)}__:', value='<https://github.com/maduck/GoWDiscordTeamBot>',
                    inline=False)
        await self.answer(message, e)

    @owner_required
    async def stats(self, message, lang, **kwargs):
        color = discord.Color.from_rgb(*RARITY_COLORS['Mythic'])
        e = discord.Embed(title=_('[PVPSTATS]', lang), description='<https://garyatrics.com/>', color=color)
        collections = [
            f'**{_("[GUILD]", lang)} {_("[AMOUNT]", lang)}**: {len(self.guilds)}',
            f'**{_("[NEWS]", lang)} {_("[CHANNELS]", lang)} (PC)**: {sum([s.get("pc", True) for s in self.subscriptions])}',
            f'**{_("[NEWS]", lang)} {_("[CHANNELS]", lang)} (Switch)**: {sum([s.get("switch", True) for s in self.subscriptions])}',
            f'**{_("[PETRESCUE]", lang)} ({_("[JUST_NOW]", lang)})**: {len(self.pet_rescues)}',
        ]
        e.add_field(name=_("[COLLECTION]", lang), value='\n'.join(collections))

        await self.answer(message, e)

    async def events(self, message, lang, **kwargs):
        events = self.expander.get_events(lang)
        e = self.views.render_events(events, kwargs.get('filter'), lang)
        await self.answer(message, e)

    async def color_kingdoms(self, message, lang, **kwargs):
        kingdoms = self.expander.get_color_kingdoms(lang)
        e = self.views.render_color_kingdoms(kingdoms, lang)
        await self.answer(message, e)

    async def troop_type_kingdoms(self, message, lang, **kwargs):
        kingdoms = self.expander.get_type_kingdoms(lang)
        e = self.views.render_type_kingdoms(kingdoms, lang)
        await self.answer(message, e)

    async def event_kingdoms(self, message, lang, **kwargs):
        events = self.expander.get_event_kingdoms(lang)
        e = self.views.render_event_kingdoms(events)
        await self.answer(message, e)

    async def levels(self, message, lang, **kwargs):
        levels = self.expander.get_levels(lang)
        e = self.views.render_levels(levels)
        await self.answer(message, e)

    async def help(self, message, lang, **kwargs):
        prefix = self.prefix.get(message.guild)
        lang = LANGUAGE_CODE_MAPPING.get(lang, lang)
        e = self.views.render_help(prefix, lang)
        await self.answer(message, e)

    async def show_tower_help(self, message, prefix, lang, **kwargs):
        e = self.views.render_tower_help(prefix, lang)
        await self.answer(message, e)

    async def quickhelp(self, message, lang, **kwargs):
        prefix = self.prefix.get(message.guild)
        e = self.views.render_quickhelp(prefix, lang, LANGUAGES)
        await self.answer(message, e)

    async def on_message(self, message):
        if message.author.bot:
            return

        await self.wait_until_ready()

        user_command = message.content.strip()
        my_prefix = self.prefix.get(message.guild)
        function, params = await self.get_function_for_command(user_command, my_prefix)
        if not function:
            return

        params['lang'] = params.get('lang') or self.language.get(message.guild)
        params['lang'] = params['lang'].lower()
        debug(message)
        await function(message=message, **params)

    @guild_required
    @admin_required
    async def change_prefix(self, message, new_prefix, **kwargs):
        my_prefix = self.prefix.get(message.guild)
        if len(new_prefix) != 1:
            e = self.generate_response('Prefix change', self.RED, 'Error',
                                       f'Your new prefix has to be 1 characters long,'
                                       f' `{new_prefix}` has {len(new_prefix)}.')
            await self.answer(message, e)
            return
        await self.prefix.set(message.guild, new_prefix)
        e = self.generate_response('Administrative action', self.RED, 'Prefix change',
                                   f'Prefix was changed from `{my_prefix}` to `{new_prefix}`')
        await self.answer(message, e)
        log.debug(f'[{message.guild.name}] Changed prefix from {my_prefix} to {new_prefix}')

    async def handle_search(self, message, search_term, lang, title, shortened=False, formatter='{0[name]} `#{0[id]}`',
                            **kwargs):
        search_function = getattr(self.expander, 'search_{}'.format(title.lower()))
        result = search_function(search_term, lang)
        if not result:
            e = discord.Embed(title=f'{title} search for `{search_term}` did not yield any result',
                              description=':(',
                              color=self.BLACK)
        elif len(result) == 1:
            view = getattr(self.views, 'render_{}'.format(title.lower()))
            e = view(result[0], shortened)
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
    pet = partialmethod(handle_search, title='Pet')
    weapon = partialmethod(handle_search, title='Weapon')
    affix = partialmethod(handle_search, title='Affix',
                          formatter='{0[name]} ({0[num_weapons]} {0[weapons_title]})')
    troop = partialmethod(handle_search, title='Troop')
    trait = partialmethod(handle_search, title='Trait', formatter='{0[name]}')
    talent = partialmethod(handle_search, title='Talent', formatter='{0[name]}')
    traitstones = partialmethod(handle_search, title='Traitstone', formatter='{0[name]}')

    async def pet_rescue(self, message, search_term, lang, time_left=59, mention='', **kwargs):
        pets = self.expander.search_pet(search_term, lang)
        if len(pets) != 1:
            e = discord.Embed(title=f'Pet search for `{search_term}` yielded {len(pets)} results.',
                              description='Try again with a different search.',
                              color=self.BLACK)
            return await self.answer(message, e)
        pet = pets[0]

        rescue = PetRescue(pet, time_left, message, mention, lang, self.answer, self.pet_rescue_config)
        e = self.views.render_pet_rescue(rescue)
        await rescue.create_or_edit_posts(e)
        await rescue.add(self.pet_rescues)

    async def show_pet_rescue_config(self, message, lang, **kwargs):
        config = self.pet_rescue_config.get(message.channel)

        e = self.views.render_pet_rescue_config(config, lang)
        await self.answer(message, e)

    @admin_required
    async def set_pet_rescue_config(self, message, key, value, lang, **kwargs):
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

    async def class_summary(self, message, lang, **kwargs):
        result = self.expander.search_class('summary', lang)
        result.sort(key=operator.itemgetter('name'))

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

    async def kingdom_summary(self, message, lang, **kwargs):
        result = self.expander.search_kingdom('summary', lang)
        result.sort(key=operator.itemgetter('name'))

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

    @staticmethod
    def generate_response(title, color, name, value):
        e = discord.Embed(title=title, color=color)
        e.add_field(name=name, value=value)
        return e

    async def handle_team_code(self, message, lang, team_code, shortened='', **kwargs):
        team = self.expander.get_team_from_message(team_code, lang)
        if not team or not team['troops']:
            log.debug(f'nothing found in message {team_code}.')
            return
        author = message.author.display_name
        author = await pluralize_author(author)
        e = self.views.render_team(team, author, shortened)
        await self.answer(message, e)

    async def waffles(self, message, **kwargs):
        waffle_no = random.randint(0, 66)
        e = self.generate_response('Waffles', self.WHITE, 'random waffle', f'number {waffle_no}')
        e.set_image(url=f'https://garyatrics.com/images/waffles/{waffle_no:03d}.jpg')
        await self.answer(message, e)

    async def show_prefix(self, message, prefix, **kwargs):
        e = self.generate_response('Prefix', self.WHITE, 'The current prefix is', f'`{prefix}`')
        await self.answer(message, e)

    @guild_required
    async def show_tower_config(self, message, prefix, **kwargs):
        e = self.tower_data.format_output_config(prefix=prefix, guild=message.guild, color=self.WHITE)
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def set_tower_config_option(self, message, option, value, **kwargs):
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
    async def set_tower_config_alias(self, message, category, field, values, **kwargs):
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
    async def show_tower_data(self, message, **kwargs):
        _range = kwargs.get('range')
        shortened = kwargs.get('shortened')
        e = self.tower_data.format_output(guild=message.guild, channel=message.channel,
                                          color=self.WHITE, prefix=kwargs['prefix'], _range=_range, shortened=shortened)
        await self.answer(message, e)

    @guild_required
    async def edit_tower_single(self, message, floor, room, scroll, **kwargs):
        success, response = self.tower_data.edit_floor(message=message, floor=floor, room=room, scroll=scroll)
        if self.tower_data.get(message.guild)['short']:
            return await self.react(message, bool_to_emoticon(success))

        e = self.generate_response('Tower of Doom', self.WHITE, 'Success' if success else 'Failure', response)
        await self.answer(message, e)

    @guild_required
    async def edit_tower_floor(self, message, floor, scroll_ii, scroll_iii, scroll_iv, scroll_v, scroll_vi=None,
                               **kwargs):

        rooms = ('ii', 'iii', 'iv', 'v', 'vi')
        scrolls = (scroll_ii, scroll_iii, scroll_iv, scroll_v, scroll_vi)

        rooms = [
            self.tower_data.edit_floor(message=message, floor=floor, room=room, scroll=scrolls[room_id])
            for room_id, room in enumerate(rooms[:-1])
        ]
        success = all([r[0] for r in rooms])

        if self.tower_data.get(message.guild)['short']:
            return await self.react(message, bool_to_emoticon(success))

        e = discord.Embed(title='Tower of Doom', color=self.WHITE)
        edit_text = '\n'.join([
            f"{'Success' if room[0] else 'Failure'}: {room[1]}"
            for room in rooms])

        e.add_field(name='Edit Tower (Floor)', value=edit_text)
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def reset_tower_config(self, message, **kwargs):
        self.tower_data.reset_config(message.guild)

        e = self.generate_response('Administrative action', self.RED, 'Success', 'Cleared tower config')
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def clear_tower_data(self, message, prefix, **kwargs):
        self.tower_data.clear_data(message)
        e = self.generate_response('Tower of Doom', self.WHITE, 'Success',
                                   f'Cleared tower data for #{message.channel.name}')
        await self.answer(message, e)

    @guild_required
    async def show_permissions(self, message, **kwargs):
        channel_permissions = message.channel.permissions_for(message.guild.me)
        permissions = {}
        for permission in self.NEEDED_PERMISSIONS:
            has_permission = getattr(channel_permissions, permission)
            permissions[permission] = '✅' if has_permission else '❌'
        e = self.views.render_permissions(message.channel, permissions)
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def news_subscribe(self, message, platform, **kwargs):
        if not platform:
            platform = CONFIG.get('default_news_platform')
        await self.subscriptions.add(message.guild, message.channel, platform)

        e = self.generate_response('News management', self.WHITE,
                                   f'News for {platform.title()}',
                                   f'Channel {message.channel.name} is now subscribed and will receive future news.')
        await self.answer(message, e)

    async def show_toplist(self, message, toplist_id, lang, **kwargs):
        toplist = self.expander.translate_toplist(toplist_id, lang)
        e = self.views.render_toplist(toplist)
        await self.answer(message, e)

    async def create_toplist(self, message, description, items, lang, **kwargs):
        try:
            toplist = await self.expander.create_toplist(message, description, items, lang, update_id=kwargs.get('_id'))
            e = self.views.render_toplist(toplist)
        except ToplistError as te:
            e = self.generate_response('Toplist', self.BLACK, 'There was a problem', str(te))
        await self.answer(message, e)

    update_toplist = create_toplist

    async def append_toplist(self, message, _id, items, lang, **kwargs):
        try:
            await self.expander.toplists.append(_id, message.author.id, message.author.display_name, items)
            toplist = self.expander.translate_toplist(_id, lang)
            e = self.views.render_toplist(toplist)
        except ToplistError as te:
            e = self.generate_response('Toplist', self.BLACK, 'There was a problem', str(te))
        await self.answer(message, e)

    async def delete_toplist(self, message, _id, **kwargs):
        try:
            await self.expander.toplists.remove(message.author.id, _id)
            e = self.generate_response('Toplist', self.WHITE, 'Deletion', f'Toplist `{_id}` was successfully deleted.')
        except ToplistError as te:
            e = self.generate_response('Toplist', self.BLACK, 'There was a problem', str(te))
        await self.answer(message, e)

    async def show_my_toplists(self, message, **kwargs):
        toplists = self.expander.toplists.get_my_toplists(message.author.id)
        e = self.views.render_my_toplists(toplists, message.author.display_name)
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def news_unsubscribe(self, message, **kwargs):
        await self.subscriptions.remove(message.guild, message.channel)

        e = self.generate_response('News management', self.WHITE, f'News for all platforms',
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

        e = self.generate_response('News management', self.WHITE, 'Status', answer_text)
        await self.answer(message, e)

    async def class_level(self, message, **kwargs):
        def xp_for(level):
            return int(1 / 2 * (level ** 2 + level))

        low, high = sorted([
            int(kwargs.get('from') if kwargs.get('from') else 0),
            int(kwargs.get('to'))
        ])
        low = max(0, low)
        high = min(100, high)

        xp_required = xp_for(high) - xp_for(low)
        lang = kwargs.get('lang', 'en')
        e = self.views.render_class_level(low, high, xp_required, lang)
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
            embeds = self.views.render_news(article)
            for subscription in self.subscriptions:
                relevant_news = subscription.get(article['platform'])
                if not relevant_news:
                    continue
                channel = self.get_channel(subscription['channel_id'])
                if not channel:
                    log.debug(f'Subscription {subscription} is broken, skipping.')
                    continue
                log.debug(f'Sending [{article["platform"]}] {article["title"]} to {channel.guild.name}/{channel.name}.')
                if not await self.is_writable(channel):
                    message = 'is not writable' if channel else 'does not exist'
                    log.debug(f'Channel {message}.')
                    continue
                try:
                    for e in embeds:
                        await channel.send(embed=e)
                except Exception as ex:
                    log.error('Could not send out news, exception follows')
                    log.error(repr(e.fields))
                    log.exception(ex)
        with open(NewsDownloader.NEWS_FILENAME, 'w') as f:
            f.write('[]')

    @guild_required
    @admin_required
    async def change_language(self, message, new_language, **kwargs):
        my_language = self.language.get(message.guild)
        if new_language not in LANGUAGES:
            e = discord.Embed(title='Default Language', color=self.BLACK)
            e.add_field(name='Error',
                        value=f'`{new_language}` is not a valid language code.')
            self.add_available_languages(e)
            await self.answer(message, e)
            return

        await self.language.set(message.guild, new_language)
        e = self.generate_response('Default Language', self.WHITE, f'Default language for {message.guild}',
                                   f'Default language was changed from `{my_language}` to `{new_language}`.')
        await self.answer(message, e)
        log.debug(f'[{message.guild.name}] Changed language from {my_language} to {new_language}.')

    @guild_required
    async def show_languages(self, message, **kwargs):
        e = discord.Embed(title='Default Language', color=self.WHITE)
        e.add_field(name=f'Default language for {message.guild}',
                    value=f'`{self.language.get(message.guild)}`', inline=False)

        self.add_available_languages(e)
        await self.answer(message, e)

    async def tools(self, message, **kwargs):
        e = self.views.render_tools()
        await self.answer(message, e)

    @staticmethod
    def add_available_languages(e):
        available_langs = ', '.join([f'`{lang_code}`' for lang_code in LANGUAGES])
        e.add_field(name='Available languages', value=available_langs, inline=False)

    async def register_slash_commands(self):
        log.debug('Deregistering all slash commands...')
        guild_id = CONFIG.get('slash_command_guild_id')
        for command in await get_all_commands(self.user.id, TOKEN, guild_id=guild_id):
            await remove_slash_command(self.user.id, TOKEN, guild_id, command['id'])
        if not CONFIG.get('register_slash_commands'):
            return
        log.debug(f'Registering slash commands...')
        for command in COMMAND_REGISTRY:
            if 'description' not in command:
                continue
            await add_slash_command(self.user.id,
                                    bot_token=TOKEN,
                                    guild_id=guild_id,
                                    cmd_name=command['function'],
                                    description=command['description'],
                                    options=command.get('options', []))


if __name__ == '__main__':
    client = DiscordBot()
    bot_tasks.task_check_for_news.start(client)
    bot_tasks.task_check_for_data_updates.start(client)
    bot_tasks.task_update_pet_rescues.start(client)
    if TOKEN is not None:
        client.run(TOKEN)
    else:
        log.error('FATAL ERROR: DISCORD_TOKEN env var was not specified.')
