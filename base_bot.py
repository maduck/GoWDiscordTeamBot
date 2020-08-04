import logging

import discord

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
    BASE_GUILD = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.permissions = self.generate_permissions()
        self.invite_url = ''
        self.my_emojis = {}

    async def generate_embed_from_text(self, message_lines, title, subtitle):
        e = discord.Embed(title=title, color=self.WHITE)
        message_text = ''
        field_title = subtitle
        for line in message_lines:
            if len(message_text) + len(line) > 1024:
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

    async def react(self, message, reaction: discord.Emoji):
        if message.guild:
            await self.check_for_needed_permissions(message)
        try:
            await message.add_reaction(emoji=reaction)
        except discord.errors.Forbidden:
            log.warning(f'[{message.guild}][{message.channel}] Could not post response, channel is forbidden for me.')
        except EmbedLimitsExceed as e:
            log.warning(f'[{message.guild}][{message.channel}] Could not post response, embed limits exceed: {e}.')

    async def answer(self, message, embed: discord.Embed):
        if message.guild:
            await self.check_for_needed_permissions(message)
        try:
            self.embed_check_limits(embed)
            await message.channel.send(embed=embed)
        except discord.errors.Forbidden:
            log.warning(f'[{message.guild}][{message.channel}] Could not post response, channel is forbidden for me.')
        except EmbedLimitsExceed as e:
            log.warning(f'[{message.guild}][{message.channel}] Could not post response, embed limits exceed: {e}.')

    async def on_guild_join(self, guild):
        log.debug(f'Joined guild {guild} (id {guild.id}) Now in {len(self.guilds)} guilds.')

    async def on_guild_remove(self, guild):
        log.debug(f'Guild {guild} (id {guild.id}) kicked me out. Now in {len(self.guilds)} guilds.')

    async def update_base_emojis(self):
        home_guild = discord.utils.find(lambda g: g.name == self.BASE_GUILD, self.guilds)
        for emoji in home_guild.emojis:
            self.my_emojis[emoji.name] = str(emoji)

    @staticmethod
    def is_guild_admin(message):
        has_admin_role = 'admin' in [r.name.lower() for r in message.author.roles]
        is_administrator = any([r.permissions.administrator for r in message.author.roles])
        is_owner = message.author == message.guild.owner
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
        if getattr(embed, '_footer', None):
            if len(embed.footer.text) > 2048:
                raise EmbedLimitsExceed('embed.footer.text')
        if getattr(embed, '__author', None):
            if len(embed.author.name) > 256:
                raise EmbedLimitsExceed('embed.author.name')
        if len(embed) > 6000:
            raise EmbedLimitsExceed('total length of embed')

    @staticmethod
    def trim_text_lines_to_length(lines, limit):
        breakdown = [sum([len(c) for c in lines[0:i]]) < limit for i in range(len(lines))]
        if all(breakdown):
            return lines
        return lines[:breakdown.index(False) - 1]

    @staticmethod
    def trim_news_to_length(text, link, max_length=1000):
        break_character = '\n'
        input_text = f'{text}{break_character}'
        trimmed_text = input_text[:input_text[:max_length].rfind(break_character)]
        read_more = ''
        if len(trimmed_text + break_character) != len(input_text):
            read_more = '[...] '
        result = f'{trimmed_text}{read_more}\n\n[Read full news article]({link}).'
        return result
