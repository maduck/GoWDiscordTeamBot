import asyncio

import discord

from models import DB


class PetRescueConfig:
    DEFAULT_CONFIG = {
        'mention': '@everyone',
        'delete_mention': True,
        'delete_message': True,
        'delete_pet': True,
    }

    def __init__(self):
        self.__data = {}

    async def load(self):
        lock = asyncio.Lock()
        async with lock:
            db = DB()
            query = 'SELECT * FROM PetRescueConfig;'
            db.cursor.execute(query)
            self.__data = {
                entry['channel_id']: {
                    'mention': entry['mention'],
                    'delete_mention': bool(entry['delete_mention']),
                    'delete_message': bool(entry['delete_message']),
                    'delete_pet': bool(entry['delete_pet']),
                }
                for entry in db.cursor.fetchall()
            }

    def get(self, channel):
        return self.__data.get(channel.id, self.DEFAULT_CONFIG.copy())

    @staticmethod
    def atobool(input_value, translated_trues):
        true_values = ['on', '1', 'true', 'yes']
        true_values.extend(translated_trues)
        for item in true_values:
            if item in input_value.lower():
                return True
        return False

    async def update(self, guild, channel, key, value, translated_trues):
        translations = {
            'delete_message': self.atobool,
            'delete_mention': self.atobool,
            'delete_pet': self.atobool,
        }

        def noop(x, _):
            return x

        config = self.get(channel)
        config[key] = translations.get(key, noop)(value, translated_trues)
        await self.set(guild, channel, config)
        return config

    async def set(self, guild, channel, config):
        lock = asyncio.Lock()
        async with lock:
            self.__data[channel.id] = config
            db = DB()
            query = """
            INSERT INTO PetRescueConfig (guild_name, guild_id, channel_name, channel_id, mention, delete_mention,
             delete_message, delete_pet)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)
              ON CONFLICT (guild_id, channel_id)
              DO UPDATE SET guild_name=?, guild_id=?, channel_name=?, channel_id=?, mention=?, delete_mention=?,
               delete_message=?, delete_pet=?;"""
            channel_type = channel.type
            if channel_type == discord.ChannelType.private:
                guild_name = 'Private Message'
                guild_id = 0
                channel_name = channel.recipient.name
            else:
                guild_id = guild.id
                guild_name = guild.name
                channel_name = channel.name
            params = [
                guild_name,
                guild_id,
                channel_name,
                channel.id,
                config['mention'],
                config['delete_mention'],
                config['delete_message'],
                config['delete_pet'],
            ]
            db.cursor.execute(query, (*params, *params))
            db.commit()
            db.close()
