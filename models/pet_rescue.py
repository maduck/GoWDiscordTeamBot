import asyncio
import discord


class PetRescue:
    SECONDS_PER_MINUTE = 60

    def __init__(self, pet, time_left, message, mention, answer_method):
        self.pet = pet
        self.time_left = int(time_left or 59)
        if self.time_left >= 60:
            self.time_left = 59
        self.message = message
        self.mention = mention
        self.answer_method = answer_method

        self.alert_message = None
        self.pet_message = None

    def update_mention(self):
        if not self.mention and self.message.guild:
            self.mention = self.message.guild.default_role
        elif not self.mention:
            self.mention = self.message.author.mention

    @property
    def reminder(self):
        return f'{self.mention} {self.pet["name"]}'

    async def create_or_edit_posts(self, embed):
        if self.pet_message:
            try:
                await self.pet_message.edit(embed=embed)
            except discord.errors.NotFound:
                return
        else:
            self.update_mention()
            self.alert_message = await self.answer_method(self.message, embed=None, content=self.reminder)
            self.pet_message = await self.answer_method(self.message, embed)

    async def delete_messages(self):
        try:
            await self.pet_message.delete()
            await self.alert_message.delete()
        except discord.errors.Forbidden:
            pass

    async def sleep_one_minute(self):
        await asyncio.sleep(self.SECONDS_PER_MINUTE)
