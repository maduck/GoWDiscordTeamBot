import discord

from configurations import CONFIG


def guild_required(function):
    async def wrapper(*args, **kwargs):
        message = kwargs['message']
        if not message.guild:
            self = args[0]
            e = discord.Embed(title='Restricted Command', color=self.RED)
            e.add_field(name='Error',
                        value=f'This command is not available in private messages.')
            await self.answer(message, e)
            return
        await function(*args, **kwargs)

    return wrapper


def admin_required(function):
    async def wrapper(*args, **kwargs):
        self = args[0]
        message = kwargs['message']
        if not self.is_guild_admin(message):
            e = discord.Embed(title='Administrative change', color=self.RED)
            e.add_field(name='Error',
                        value=f'You need to be server owner or administrator to use this command.')
            await self.answer(message, e)
            return
        await function(*args, **kwargs)

    return wrapper


def owner_required(function):
    async def wrapper(*args, **kwargs):
        self = args[0]
        message = kwargs['message']
        is_special = message.author.id in CONFIG.get('special_users')
        if not await self.is_owner(message) and not is_special:
            e = discord.Embed(title='Owner command', color=self.RED)
            e.add_field(name='Error',
                        value=f'Only the bot owner has permission to use this command.')
            await self.answer(message, e)
            return
        await function(*args, **kwargs)

    return wrapper
