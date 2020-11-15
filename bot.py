#!/usr/bin/env python3
import datetime
import json
import operator
import os
import random
from functools import partialmethod

import discord
import humanize

import bot_tasks
import models
from base_bot import BaseBot, log
from command_registry import COMMAND_REGISTRY
from configurations import CONFIG
from discord_helpers import admin_required, guild_required
from game_constants import CAMPAIGN_COLORS
from help import get_help_text, get_tower_help_text
from jobs.news_downloader import NewsDownloader
from team_expando import TeamExpander, _
from tower_data import TowerOfDoomData
from translations import HumanizeTranslator, LANGUAGES, LANGUAGE_CODE_MAPPING
from util import bool_to_emoticon, chunks, debug, pluralize_author
from views import Views

TOKEN = os.getenv('DISCORD_TOKEN')


class DiscordBot(BaseBot):
    BOT_NAME = 'garyatrics.com'
    VERSION = '0.17.1'
    NEEDED_PERMISSIONS = [
        'add_reactions',
        'read_messages',
        'send_messages',
        'embed_links',
        'attach_files',
        'external_emojis',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        log.debug(f'--------------------------- Starting {self.BOT_NAME} v{self.VERSION} --------------------------')

        self.expander = TeamExpander()
        self.tower_data = TowerOfDoomData()
        self.prefix = models.Prefix(CONFIG.get('default_prefix'))
        self.language = models.Language(CONFIG.get('default_language'))
        self.subscriptions = models.Subscriptions()
        self.views = Views(emojis={})

    async def on_ready(self):
        if not self.bot_connect:
            self.bot_connect = datetime.datetime.now()
            log.debug(f'Connected at {self.bot_connect}.')
        else:
            await self.on_resumed()
        self.invite_url = f'https://discordapp.com/api/oauth2/authorize' \
                          f'?client_id={self.user.id}' \
                          f'&scope=bot' \
                          f'&permissions={self.permissions.value}'
        log.info(f'Logged in as {self.user.name}')

        subscriptions = sum([s.get('pc', True) for s in self.subscriptions])
        log.info(f'{subscriptions} channels subscribed to news.')
        log.info(f'Active in {len(self.guilds)} guilds.')

        game = discord.Game("Gems of War")
        await self.change_presence(status=discord.Status.online, activity=game)
        await self.update_base_emojis()
        self.views.my_emojis = self.my_emojis

    async def get_function_for_command(self, user_command, user_prefix):
        for command in COMMAND_REGISTRY:
            match = command['pattern'].search(user_command)
            if not match:
                continue
            groups = match.groupdict()

            if groups.get('prefix', user_prefix) == user_prefix:
                return getattr(self, command['function']), groups
        return None, None

    async def show_campaign_tasks(self, message, lang, tier, **kwargs):
        campaign_data = self.expander.get_campaign_tasks(lang, tier)
        if not campaign_data['has_content']:
            title = _('[NO_CURRENT_TASK]', lang)
            description = _('[CAMPAIGN_COMING_SOON]', lang)
            e = discord.Embed(title=title, description=description, color=self.WHITE)
            return await self.answer(message, e)

        for category, tasks in campaign_data['campaigns'].items():
            category_lines = [f'**{task["title"]}**: {task["name"]}' for task in tasks]
            color = CAMPAIGN_COLORS.get(category, self.WHITE)
            e = discord.Embed(title=f'__**{category}**__', description='\n'.join(category_lines), color=color)
            await self.answer(message, e)

    async def show_spoilers(self, message, lang, _filter, **kwargs):
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

    async def show_soulforge(self, message, lang, **kwargs):
        title, craftable_items = self.expander.get_soulforge(lang)
        e = discord.Embed(title=title, color=self.WHITE)
        for category, recipes in craftable_items.items():
            recipes = sorted(recipes, key=operator.itemgetter('rarity', 'id'))
            message_lines = '\n'.join([f'{r["name"]} `{r["id"]}`' for r in recipes])
            e.add_field(name=category, value=message_lines, inline=False)
        await self.answer(message, e)

    async def show_uptime(self, message, lang, **kwargs):
        e = discord.Embed(title='Uptime', color=self.WHITE)
        lang = LANGUAGE_CODE_MAPPING.get(lang, lang)
        with HumanizeTranslator(lang) as _t:
            uptime = humanize.naturaltime(self.bot_start)
            downtime = humanize.naturaldelta(self.downtimes)
        e.add_field(name='Bot running since', value=uptime, inline=False)
        e.add_field(name='Offline for', value=downtime, inline=False)
        bot_runtime = datetime.datetime.now() - self.bot_start
        availability = (bot_runtime - self.downtimes) / bot_runtime
        e.add_field(name='Availability', value=f'{availability:.3%}')
        await self.answer(message, e)

    async def show_version(self, message, **kwargs):
        e = discord.Embed(title='Version', description=self.VERSION, color=self.WHITE)
        await self.answer(message, e)

    async def show_events(self, message, lang, **kwargs):
        events = self.expander.get_events(lang)
        e = self.views.render_events(events)
        await self.answer(message, e)

    async def show_levels(self, message, lang, **kwargs):
        levels = self.expander.get_levels(lang)
        e = self.views.render_levels(levels)
        await self.answer(message, e)

    async def show_help(self, message, prefix, lang, **kwargs):
        help_title, help_text = get_help_text(prefix, lang)

        e = discord.Embed(title=help_title, color=self.WHITE)
        for section, text in help_text.items():
            e.add_field(name=section, value=text, inline=False)
        await self.answer(message, e)

    async def show_tower_help(self, message, prefix, lang, **kwargs):
        help_title, help_text = get_tower_help_text(prefix, lang)

        e = discord.Embed(title=help_title, color=self.WHITE)
        for section, text in help_text.items():
            e.add_field(name=section, value=text, inline=False)
        await self.answer(message, e)

    async def show_quickhelp(self, message, prefix, **kwargs):
        e = discord.Embed(title='Quick Help', color=self.WHITE)
        langs = '|'.join(LANGUAGES)
        e.add_field(name='How to read',
                    value='Square brackets `[]` show optional parameters, except for troop code.\n'
                          'Vertical lines `|` mean "or": this|that.\n'
                          f'valid language codes are `{langs}`.')
        e.add_field(name='Searches',
                    value=f'`{prefix}help`\n'
                          f'`{prefix}quickhelp`\n'
                          f'`{prefix}towerhelp`\n'
                          f'`[lang][-][<troopcode>]`\n'
                          f'`[lang][-]{prefix}troop <search>`\n'
                          f'`[lang][-]{prefix}weapon <search>`\n'
                          f'`[lang][-]{prefix}pet <search>`\n'
                          f'`[lang][-]{prefix}class <search>`\n'
                          f'`[lang][-]{prefix}kingdom <search>`\n'
                          f'`[lang][-]{prefix}talent <search>`\n'
                          f'`[lang][-]{prefix}trait <search>`\n'
                          f'`[lang][-]{prefix}traitstone <search>`\n',
                    inline=False)
        e.add_field(name='Overviews',
                    value=f'`[lang]{prefix}class summary`\n'
                          f'`[lang]{prefix}kingdom summary`\n'
                          f'`[lang]{prefix}spoiler[s] [pet[s]|troop[s]|weapon[s]|kingdom[s]|event[s]]`\n'
                          f'`[lang]{prefix}event[s]`\n'
                          f'`[lang]{prefix}campaign [bronze|silver|gold]`\n'
                          f'`[lang]{prefix}soulforge`\n'
                          f'`[lang]{prefix}levels`\n',
                    inline=False)
        e.add_field(name='Admin Commands',
                    value=f'`{prefix}towerconfig`\n'
                          f'`{prefix}towerclear`\n'
                          f'`{prefix}news [[un]subscribe [pc|switch]]`\n'
                          f'`{prefix}prefix [new_prefix]`\n'
                          f'`{prefix}lang[uage[s]] [new_language]`\n',
                    inline=False)
        e.add_field(name='Bot specific',
                    value=f'`{prefix}version`\n'
                          f'`{prefix}uptime`\n'
                          f'`{prefix}invite`\n'
                          f'`{prefix}waffles`\n',
                    inline=False
                    )
        await self.answer(message, e)

    async def on_message(self, message):
        if message.author.bot:
            return

        user_command = message.content.lower().strip()
        my_prefix = self.prefix.get(message.guild)
        function, params = await self.get_function_for_command(user_command, my_prefix)
        if not function:
            return

        params['lang'] = params.get('lang') or self.language.get(message.guild)
        debug(message)
        await function(message=message, **params)

    async def show_invite_link(self, message, **kwargs):
        e = self.generate_response('Bot invite link', self.WHITE, 'Feel free to share!', self.invite_url)
        await self.answer(message, e)

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

    async def handle_search(self, message, search_term, lang, title, shortened, formatter='{0[name]} `#{0[id]}`',
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
            item_chunks = chunks(items_found, 30)
            for i, chunk in enumerate(item_chunks):
                chunk_message = '\n'.join(chunk)
                e.add_field(name=f'results {30 * i + 1} - {30 * i + len(chunk)}', value=chunk_message)
        await self.answer(message, e)

    handle_class_search = partialmethod(handle_search, title='Class')
    handle_kingdom_search = partialmethod(handle_search, title='Kingdom')
    handle_pet_search = partialmethod(handle_search, title='Pet')
    handle_weapon_search = partialmethod(handle_search, title='Weapon')
    handle_affix_search = partialmethod(handle_search, title='Affix',
                                        formatter='{0[name]} ({0[num_weapons]} {0[weapons_title]})')
    handle_troop_search = partialmethod(handle_search, title='Troop')
    handle_trait_search = partialmethod(handle_search, title='Trait', formatter='{0[name]}')
    handle_talent_search = partialmethod(handle_search, title='Talent', formatter='{0[name]}')
    handle_traitstone_search = partialmethod(handle_search, title='Traitstone', formatter='{0[name]}')

    async def show_class_summary(self, message, lang, **kwargs):
        result = self.expander.search_class('summary', lang)
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
        await self.answer(message, e)

    async def show_kingdom_summary(self, message, lang, **kwargs):
        result = self.expander.search_kingdom('summary', lang)
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
        e = self.tower_data.format_output(guild=message.guild, channel=message.channel,
                                          color=self.WHITE, prefix=kwargs['prefix'])
        await self.answer(message, e)

    @guild_required
    async def edit_tower_single(self, message, floor, room, scroll, **kwargs):
        my_data = self.tower_data.get(message.guild)
        short = my_data["short"]
        success, response = self.tower_data.edit_floor(message=message, floor=floor, room=room, scroll=scroll)
        if short:
            await self.react(message, bool_to_emoticon(success))
        else:
            e = self.generate_response('Tower of Doom', self.WHITE, 'Success' if success else 'Failure', response)
            await self.answer(message, e)

    @guild_required
    async def edit_tower_floor(self, message, floor, scroll_ii, scroll_iii, scroll_iv, scroll_v, scroll_vi=None,
                               **kwargs):

        my_data = self.tower_data.get(message.guild)
        short = my_data['short']

        rooms = ('ii', 'iii', 'iv', 'v', 'vi')
        scrolls = (scroll_ii, scroll_iii, scroll_iv, scroll_v, scroll_vi)

        rooms = [
            self.tower_data.edit_floor(message=message, floor=floor, room=room, scroll=scrolls[room_id])
            for room_id, room in enumerate(rooms[:-1])
        ]
        success = all([r[0] for r in rooms])

        if short:
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
    @admin_required
    async def news_subscribe(self, message, platform, **kwargs):
        if not platform:
            platform = CONFIG.get('default_news_platform')
        await self.subscriptions.add(message.guild, message.channel, platform)

        e = self.generate_response('News management', self.WHITE,
                                   f'Subscribe for {platform.title()}',
                                   f'News will now be posted into channel {message.channel.name}.')
        await self.answer(message, e)

    @guild_required
    @admin_required
    async def news_unsubscribe(self, message, **kwargs):
        await self.subscriptions.remove(message.guild, message.channel)

        e = self.generate_response('News management', self.WHITE, 'Unsubscribe',
                                   f'News will *not* be posted into channel {message.channel.name}.')
        await self.answer(message, e)

    @guild_required
    async def news_status(self, message, **kwargs):
        subscribed = self.subscriptions.is_subscribed(message.guild, message.channel)
        answer_text = f'News will *not* be posted into channel {message.channel.name}.'
        if subscribed:
            platforms = ('PC', 'Switch')
            subscribed_platforms = [p for p in platforms if subscribed.get(p.lower())]
            platforms_text = ' and '.join(subscribed_platforms)
            answer_text = f'{platforms_text} news for will be posted into channel {message.channel.name}.'

        e = self.generate_response('News management', self.WHITE, 'Status', answer_text)
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
            e = discord.Embed(title='Gems of War news', color=self.WHITE, url=article['url'])
            content = self.views.trim_news_to_length(article['content'], article['url'])
            e.add_field(name=article['title'], value=content)
            embeds = [e]
            for image_url in article['images']:
                e = discord.Embed(type='image', color=self.WHITE)
                e.set_image(url=image_url)
                embeds.append(e)

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
                except Exception as e:
                    log.error('Could not send out news, exception follows')
                    log.exception(e)
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

    @staticmethod
    def add_available_languages(e):
        available_langs = ', '.join([f'`{lang_code}`' for lang_code in LANGUAGES])
        e.add_field(name='Available languages', value=available_langs, inline=False)


if __name__ == '__main__':
    client = DiscordBot()
    bot_tasks.task_check_for_news.start(client)
    bot_tasks.task_check_for_data_updates.start(client)
    if TOKEN is not None:
        client.run(TOKEN)
    else:
        log.error('FATAL ERROR: DISCORD_TOKEN env var was not specified.')
