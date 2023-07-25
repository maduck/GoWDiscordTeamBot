import datetime
import logging
import os
import sys
import traceback
from enum import Enum

import aiohttp
import discord
import requests

from configurations import CONFIG
from discord_fake_classes import FakeMessage

IMMEDIATE_RECONNECT_TIME = datetime.timedelta(milliseconds=500)

LOGLEVEL = logging.DEBUG

formatter = logging.Formatter('%(asctime)-15s [%(levelname)s] %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(LOGLEVEL)
log = logging.getLogger(__name__)

log.setLevel(logging.DEBUG)
log.addHandler(handler)


class EmbedLimitsExceed(Exception):
    pass


class InteractionResponseType(Enum):
    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
    DEFERRED_UPDATE_MESSAGE = 6
    UPDATE_MESSAGE = 7
    APPLICATION_COMMAND_AUTOCOMPLETE_RESULT = 8
    MODAL = 9


class BaseBot(discord.Client):
    WHITE = discord.Color.from_rgb(254, 254, 254)
    BLACK = discord.Color.from_rgb(0, 0, 0)
    RED = discord.Color.from_rgb(255, 0, 0)
    NEEDED_PERMISSIONS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.permissions = self.generate_permissions()
        self.invite_url = ''
        self.my_emojis = {}
        self.bot_disconnect = datetime.datetime.now()
        self.bot_start = datetime.datetime.now()
        self.bot_connect = None
        self.downtimes = datetime.timedelta(seconds=0)
        log.debug(f'__init__ reset uptime to {self.bot_start}.')

    async def on_disconnect(self):
        if self.bot_connect > self.bot_disconnect:
            self.bot_disconnect = datetime.datetime.now()
            log.debug(f'Disconnected at {self.bot_disconnect}.')

    async def on_resumed(self):
        if self.bot_disconnect > self.bot_connect:
            self.bot_connect = datetime.datetime.now()
            added_downtime = self.bot_connect - self.bot_disconnect
            if added_downtime > IMMEDIATE_RECONNECT_TIME:
                self.downtimes += added_downtime
            else:
                added_downtime = datetime.timedelta(seconds=0)
            log.debug(f'Reconnected at {self.bot_connect}, increased downtime by {added_downtime} to {self.downtimes}.')

    async def generate_embed_from_text(self, message_lines, title, subtitle):
        e = discord.Embed(title=title, color=self.WHITE)
        message_text = ''
        field_title = subtitle
        for line in message_lines:
            if len(field_title) + len(message_text) + len(line) + len('``````') > 1024:
                e.add_field(name=field_title, value=f'```{message_text}```', inline=False)
                message_text = f'{line}\n'
                field_title = 'Continuation'
            else:
                message_text += f'{line}\n'
        e.add_field(name=field_title, value=f'```{message_text}```')
        return e

    def generate_permissions(self):
        permissions = discord.Permissions.none()

        for perm_name in self.NEEDED_PERMISSIONS:
            setattr(permissions, perm_name, True)
        log.debug(f'Permissions required: {", ".join([p for p, v in permissions if v])}')
        return permissions

    @staticmethod
    async def is_writable(channel):
        if not channel:
            return False
        me = channel.guild.me
        permissions = channel.permissions_for(me)
        return permissions.send_messages

    @staticmethod
    async def react(message, reaction: discord.Emoji):
        try:
            await message.add_reaction(emoji=reaction)
        except discord.DiscordException as e:
            log.warning(f'[{message.guild}][{message.channel}] Could not post response: {e}.')

    async def answer(self, message, embed: discord.Embed, content='', no_interaction=False):
        try:
            if not embed:
                return await self.answer_or_react(message, embed, content, no_interaction)
            self.embed_check_limits(embed)
            if message.author and message.author.avatar:
                embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
            elif message.author:
                embed.set_author(name=message.author.display_name)
            return await self.answer_or_react(message, embed, content, no_interaction)
        except discord.errors.Forbidden:
            log.warning(f'[{message.guild}][{message.channel}] Could not post response, channel is forbidden for me.')
        except EmbedLimitsExceed as e:
            warning = f'[{message.guild}][{message.channel}] Could not post response, embed limits exceed: {e}.'
            e = discord.Embed(title='Error', description=warning)
            return await message.channel.send(embed=e)

    async def answer_or_react(self, message, embed: discord.Embed, content=None, no_interaction=False):
        if hasattr(message, 'interaction_id') and not no_interaction:
            return await self.send_slash_command_result(message, embed, content, file=None)
        elif not embed:
            return await message.channel.send(content=content)
        return await message.channel.send(embed=embed)

    @staticmethod
    async def send_slash_command_result(message, embed, content, file=None,
                                        response_type=InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE):
        endpoint = f'interactions/{message.interaction_id}/{message.interaction_token}/callback'
        url = f'https://discord.com/api/v10/{endpoint}'
        response = {
            'type': response_type.value,
            'data': {
                'embeds': [embed.to_dict()] if embed else [],
                'content': content,
                'allowed_mentions': {
                    'parse': ['roles', 'users', 'everyone']
                }
            },
            'flags': 0,
        }
        async with aiohttp.ClientSession() as session:
            r = await session.post(url, headers={"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"}, json=response)
            if r.status != 404:
                r.raise_for_status()
            return message.id

    async def delete_slash_command_interaction(self, message):
        endpoint = f'webhooks/{self.application_id}/{message.interaction_token}/messages/@original'
        url = f'https://discord.com/api/v8/{endpoint}'
        async with aiohttp.ClientSession() as session:
            r = await session.delete(url, headers={"Authorization": f"Bot {os.getenv('DISCORD_TOKEN')}"})
            if r.status != 404:
                r.raise_for_status()

    async def on_slash_command(self, function, options, message):
        return NotImplemented

    async def on_interaction(self, interaction):
        channel = interaction.channel
        guild = interaction.guild
        author = interaction.user
        func = getattr(self, interaction.data['name'])
        options = {o['name']: o['value'] for o in interaction.data.get('options', [])}
        options_text = ' '.join([f'{k}={v}' for k, v in options.items()])
        content = f'/{interaction.data["name"]} {options_text}'
        message = FakeMessage(author, guild, channel, content, interaction.id, interaction.token)
        await self.on_slash_command(func, options, message)

    async def on_raw_reaction_add(self, payload):
        if not payload.member or payload.member.bot:
            return

        if payload.emoji.name != '❌':
            return

        channel = await self.fetch_channel(payload.channel_id)
        me = channel.guild.me
        permissions = channel.permissions_for(me)

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            log.debug(f'[{channel.guild}][{channel}][{payload.member}] '
                      f'Tried to react to an emoji for a nonexistent message: {payload}')
            return
        except discord.errors.Forbidden:
            log.debug(f'[{channel.guild}][{channel}][{payload.member}] '
                      f'Was not allowed to access message: {payload}')
            return

        if message.author != me:
            return
        if not message.embeds or payload.member.display_name != message.embeds[0].author.name:
            return
        if not permissions.manage_messages:
            await message.add_reaction('⛔')
            return

        await message.clear_reaction(payload.emoji)
        log.debug(f'[{message.guild}][{message.channel}][{payload.member.display_name}] '
                  f'requested deletion of message {message.id}')
        return await message.delete()

    async def on_guild_join(self, guild):
        log.debug(f'Joined guild {guild} (id {guild.id}) Now in {len(self.guilds)} guilds.')

    async def on_guild_remove(self, guild):
        log.debug(f'Guild {guild.name} (id {guild.id}) kicked me out. Now in {len(self.guilds)} guilds.')

    async def on_error(self, event, *args, **kwargs):
        if host := CONFIG.get('ntfy_host'):
            exception = sys.exc_info()
            data_lines = [
                f'# Bot:{self.user.display_name}',
                f'{exception[0].__name__}: {exception[1]}',
                '---',
                '```',
                ''.join(traceback.format_tb(exception[2])),
                '```',
            ]

            requests.post(host, data='\n'.join(data_lines), headers={
                'Title': f'Exception in {event}',
                'Priority': 'urgent',
                'Tags': 'rotating_light',
                'Markdown': 'yes',
            }, auth=(CONFIG.get('ntfy_user'), CONFIG.get('ntfy_pass')))
        await super().on_error(event, *args, **kwargs)

    async def update_base_emojis(self):
        for guild_id in CONFIG.get('base_guilds'):
            await self.fetch_emojis_from_guild(guild_id)

    async def fetch_emojis_from_guild(self, guild_id):
        guild = self.get_guild(guild_id)
        for emoji in guild.emojis:
            self.my_emojis[emoji.name] = str(emoji)
        log.debug(f'Loaded {len(guild.emojis)} emojis from {guild.name}')

    async def is_owner(self, message):
        app_info = await self.application_info()
        if app_info.team:
            return message.author in app_info.team.members
        return message.author == app_info.owner

    @staticmethod
    def is_guild_admin(message):
        if message.channel.type == discord.ChannelType.private:
            return True
        has_admin_role = any('admin' in r.name.lower() for r in message.author.roles)
        is_administrator = any(r.permissions.administrator for r in message.author.roles)
        is_owner = message.author.id == message.guild.owner_id
        return is_owner or is_administrator or has_admin_role

    @staticmethod
    def embed_check_limits(embed):
        if len(embed.title) > 256:
            raise EmbedLimitsExceed(f'Embed title too long: {len(embed.title)}')
        if embed.description and len(embed.description) > 4096:
            raise EmbedLimitsExceed(f'Embed description too long: {len(embed.description)}')
        if embed.fields and len(embed.fields) > 25:
            raise EmbedLimitsExceed(f'Number of embed fields: {len(embed.fields)}')
        for field in embed.fields:
            if len(field.name) > 256:
                raise EmbedLimitsExceed(f'Field name too long: {len(field.name)}')
            if len(field.value) > 1024:
                raise EmbedLimitsExceed(f'Field value too long: {len(field.value)}')
        if getattr(embed, '_footer', None) and len(embed.footer.text) > 2048:
            raise EmbedLimitsExceed(f'Footer too long: {len(embed.footer.text)}')
        if getattr(embed, '__author', None) and len(embed.author.name) > 256:
            raise EmbedLimitsExceed(f'Author name too long: {len(embed.author.name)}')
        if len(embed) > 6000:
            raise EmbedLimitsExceed(f'Total embed too big: {len(embed)}')

    @staticmethod
    def first_writable_channel(guild):
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel

    @staticmethod
    def is_interaction(message):
        return hasattr(message, 'interaction_id') and message.interaction_id
