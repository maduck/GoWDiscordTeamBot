import datetime
import logging

import discord

from configurations import CONFIG

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
            self.downtimes += added_downtime
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

    async def check_for_needed_permissions(self, message):
        channel_permissions = message.channel.permissions_for(message.guild.me)
        for permission in self.NEEDED_PERMISSIONS:
            has_permission = getattr(channel_permissions, permission)
            if not has_permission:
                log.info(f'Missing permission {permission} in channel {message.guild} / {message.channel}.')

    @staticmethod
    async def is_writable(channel):
        if not channel:
            return False
        me = channel.guild.me
        permissions = channel.permissions_for(me)
        return permissions.send_messages

    async def react(self, message, reaction: discord.Emoji):
        if message.guild:
            await self.check_for_needed_permissions(message)
        try:
            await message.add_reaction(emoji=reaction)
        except discord.errors.Forbidden:
            log.warning(f'[{message.guild}][{message.channel}] Could not post response, channel is forbidden for me.')
        except EmbedLimitsExceed as e:
            log.warning(f'[{message.guild}][{message.channel}] Could not post response, embed limits exceed: {e}.')

    async def answer(self, message, embed: discord.Embed, content=''):
        if message.guild:
            await self.check_for_needed_permissions(message)
        try:
            if not embed:
                return await message.channel.send(content=content)
            self.embed_check_limits(embed)
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
            return await message.channel.send(embed=embed)
        except discord.errors.Forbidden:
            log.warning(f'[{message.guild}][{message.channel}] Could not post response, channel is forbidden for me.')
        except EmbedLimitsExceed as e:
            log.warning(f'[{message.guild}][{message.channel}] Could not post response, embed limits exceed: {e}.')

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
        if payload.member.display_name != message.embeds[0].author.name:
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
        log.debug(f'Guild {guild} (id {guild.id}) kicked me out. Now in {len(self.guilds)} guilds.')

    async def update_base_emojis(self):
        guilds = [CONFIG.get('base_guild'), CONFIG.get('base_guild_2')]
        for guild in guilds:
            await self.fetch_emojis_from_guild(guild)

    async def fetch_emojis_from_guild(self, guild):
        my_guild = discord.utils.find(lambda g: g.name == guild, self.guilds)
        for emoji in my_guild.emojis:
            self.my_emojis[emoji.name] = str(emoji)

    @staticmethod
    def is_guild_admin(message):
        has_admin_role = any(['admin' in r.name.lower() for r in message.author.roles])
        is_administrator = any([r.permissions.administrator for r in message.author.roles])
        is_owner = message.author.id == message.guild.owner_id
        return is_owner or is_administrator or has_admin_role

    @staticmethod
    def embed_check_limits(embed):
        if len(embed.title) > 256:
            raise EmbedLimitsExceed(embed.title)
        if len(embed.description) > 2048:
            raise EmbedLimitsExceed('embed.description')
        if embed.fields and len(embed.fields) > 25:
            raise EmbedLimitsExceed('embed.fields')
        for field in embed.fields:
            if len(field.name) > 256:
                raise EmbedLimitsExceed('field.name', field)
            if len(field.value) > 1024:
                raise EmbedLimitsExceed('field.value', field)
        if getattr(embed, '_footer', None) and len(embed.footer.text) > 2048:
            raise EmbedLimitsExceed('embed.footer.text')
        if getattr(embed, '__author', None) and len(embed.author.name) > 256:
            raise EmbedLimitsExceed('embed.author.name')
        if len(embed) > 6000:
            raise EmbedLimitsExceed('total length of embed')
