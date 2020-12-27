import discord


def guild_required(function):
    async def wrapper(*args, **kwargs):
        message = kwargs['message']
        if not message.guild:
            await message.channel.send(content='This command is not available in private messages.')
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
                        value=f'Only the server owner has permission to use this command.')
            await self.answer(message, e)
            return
        await function(*args, **kwargs)

    return wrapper


def owner_required(function):
    async def wrapper(*args, **kwargs):
        self = args[0]
        message = kwargs['message']
        if not await self.is_owner(message):
            e = discord.Embed(title='Owner command', color=self.RED)
            e.add_field(name='Error',
                        value=f'Only the bot owner has permission to use this command.')
            await self.answer(message, e)
            return
        await function(*args, **kwargs)

    return wrapper
