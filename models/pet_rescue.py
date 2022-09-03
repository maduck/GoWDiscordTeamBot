import asyncio
import datetime
import math

import discord

from base_bot import FakeMessage, log
from models import DB


class PetRescue:
    SECONDS_PER_MINUTE = 60
    DISPLAY_TIME = datetime.timedelta(minutes=61)

    def __init__(self, pet, time_left, message, mention, lang, answer_method, config, override_time_left=None):
        self.pet = pet
        time_left = int(time_left or 59)
        if time_left >= 60:
            time_left = 59
        if override_time_left:
            time_left = override_time_left
        self.start_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=60 - time_left)
        self.active = True
        self.message = message
        self.mention = mention
        self.show_mention = True
        if self.mention and message.id:
            self.show_mention = False
        self.lang = lang
        self.answer_method = answer_method
        self.config = config.get(message.channel)

        self.alert_message = None
        self.pet_message = None

    def update_mention(self):
        if not self.mention and self.message.guild:
            self.mention = self.config.get('mention', self.message.guild.default_role)
        elif not self.mention:
            self.mention = self.config.get('mention', self.message.author.mention)

    @property
    def reminder(self):
        return f'{self.message.author.name}: {self.mention} {self.pet.name}'

    @staticmethod
    def get_amount():
        query = "SELECT seq FROM SQLITE_SEQUENCE WHERE name='PetRescue';"
        db = DB()
        db_result = db.cursor.execute(query).fetchone()
        if not db_result:
            return 0
        return db_result[0]

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
            except discord.errors.DiscordException as e:
                log.warn(f'Error while editing pet rescue: {str(e)}')
                await self.remove_from_db()
                self.active = False
        elif not self.pet_message:
            if self.show_mention:
                self.update_mention()
                self.alert_message = await self.answer_method(self.message, embed=None, content=self.reminder)
            self.pet_message = await self.answer_method(self.message, embed)
        else:
            await self.delete_messages()
            await self.remove_from_db()
            self.active = False

    async def delete_messages(self):
        if self.config['delete_pet']:
            await self.delete_message(self.pet_message)
        if self.config['delete_mention'] and self.alert_message:
            await self.delete_message(self.alert_message)
        if self.config['delete_message']:
            await self.delete_message(self.message)

    @staticmethod
    async def delete_message(message):
        if not message or not message.id:
            return
        try:
            await message.delete()
        except (discord.errors.Forbidden, discord.errors.NotFound, discord.errors.HTTPException):
            try:
                await message.add_reaction('⛔')
            except discord.errors.DiscordException:
                pass

    @classmethod
    async def load_rescues(cls, client):
        db = DB()
        db_result = db.cursor.execute('SELECT * FROM PetRescue;').fetchall()
        rescues = []
        broken_rescues = []
        for i, entry in enumerate(db_result, start=1):
            log.debug(f'Loading pet rescue {i} of {len(db_result)}')
            pet = client.expander.pets[entry['pet_id']][entry['lang']]

            try:
                channel = await client.fetch_channel(entry['channel_id'])
                guild = None
                if not isinstance(channel, discord.DMChannel):
                    guild = channel.guild
                message = FakeMessage('author', guild, channel, 'content')
                if entry['message_id']:
                    message = await channel.fetch_message(entry['message_id'])
            except discord.errors.DiscordException as e:
                log.warning(f'Pet rescue is broken: {e}')
                broken_rescues.append(entry['id'])
                continue
            rescue = PetRescue(
                pet=pet,
                time_left=0,
                message=message,
                mention=entry['mention'],
                lang=entry['lang'],
                answer_method=client.answer,
                config=client.pet_rescue_config,
            )
            try:
                if entry['alert_message_id']:
                    rescue.alert_message = await channel.fetch_message(entry['alert_message_id'])
                rescue.pet_message = await channel.fetch_message(entry['pet_message_id'])
            except discord.errors.DiscordException:
                broken_rescues.append(entry['id'])
                continue
            rescue.start_time = entry['start_time']
            rescues.append(rescue)
        db.close()

        if broken_rescues:
            log.debug(f'Pruning {len(broken_rescues)} broken pet rescues from the database: {broken_rescues}.')
        for rescue_id in broken_rescues:
            await cls.delete_by_id(rescue_id=rescue_id)

        return rescues

    async def add(self, pet_rescues):
        db = DB()
        query = 'INSERT INTO PetRescue (guild_name, guild_id, channel_name, channel_id, message_id, pet_id, ' \
                'alert_message_id, pet_message_id, start_time, lang, mention) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        channel_type = self.message.channel.type
        if channel_type == discord.ChannelType.private:
            channel_name = self.message.author.name
        else:
            channel_name = self.message.channel.name

        params = [
            self.message.guild.name if self.message.guild else '<Private Message>',
            self.message.guild.id if self.message.guild else 0,
            channel_name,
            self.message.channel.id,
            self.message.id,
            self.pet.id,
            self.alert_message.id if self.alert_message else 0,
            self.pet_message.id if self.pet_message else 0,
            self.start_time,
            self.lang,
            str(self.mention),
        ]
        stats_query = 'INSERT INTO PetRescueStats (pet_id, rescues) VALUES (?, ?) ' \
                      'ON CONFLICT(pet_id) DO UPDATE SET rescues = rescues + 1 WHERE pet_id = ?'
        stats_params = [self.pet.id, 1, self.pet.id]

        lock = asyncio.Lock()
        async with lock:
            db.cursor.execute(query, params)
            db.cursor.execute(stats_query, stats_params)
            db.commit()
            db.close()
            pet_rescues.append(self)

    @staticmethod
    def get_stats():
        db = DB()
        query = 'SELECT * FROM PetRescueStats'
        db.cursor.execute(query)
        return db.cursor.fetchall()

    async def remove_from_db(self):
        await self.delete_by_id(message_id=self.message.id)

    @staticmethod
    async def delete_by_id(rescue_id=0, message_id=0):
        lock = asyncio.Lock()
        async with lock:
            db = DB()
            query = 'DELETE FROM PetRescue WHERE id = ? OR message_id = ?'
            db.cursor.execute(query, [rescue_id, message_id])
            db.commit()
            db.close()
