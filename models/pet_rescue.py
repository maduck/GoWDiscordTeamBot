import datetime
import math

import discord


class PetRescue:
    SECONDS_PER_MINUTE = 60
    DISPLAY_TIME = datetime.timedelta(minutes=61)

    def __init__(self, pet, time_left, message, mention, lang, answer_method):
        self.pet = pet
        time_left = int(time_left or 59)
        if time_left >= 60:
            time_left = 59
        self.start_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=60 - time_left)
        self.active = True
        self.message = message
        self.mention = mention
        self.lang = lang
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

    @property
    def time_left(self):
        delta = self.start_time + datetime.timedelta(minutes=60) - datetime.datetime.utcnow()
        if delta.days < 0:
            return 0
        return int(math.ceil(delta.seconds / self.SECONDS_PER_MINUTE))

    async def create_or_edit_posts(self, embed):
        if self.pet_message and datetime.datetime.utcnow() - self.start_time <= self.DISPLAY_TIME:
            try:
                await self.pet_message.edit(embed=embed)
            except discord.errors.NotFound:
                return
        elif not self.pet_message:
            self.update_mention()
            self.alert_message = await self.answer_method(self.message, embed=None, content=self.reminder)
            self.pet_message = await self.answer_method(self.message, embed)
        else:
            await self.delete_messages()
            self.active = False

    async def delete_messages(self):
        try:
            await self.pet_message.delete()
            await self.alert_message.delete()
        except discord.errors.Forbidden:
            pass
