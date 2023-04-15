import asyncio

from models.db import DB


class BaseGuildStorage:
    def __init__(self, default_value):
        self.__data = {}
        self.default_value = default_value
        self.table = type(self).__name__
        self.load()

    def load(self):
        db = DB()
        result = db.cursor.execute(f'SELECT * FROM `{self.table}`;')
        self.__data = dict(result.fetchall())
        db.close()

    async def set(self, guild, value):
        self.__data[guild.id] = value
        lock = asyncio.Lock()
        async with lock:
            db = DB()
            query = f"""
            INSERT INTO {self.table} (guild_id, value)
              VALUES (?, ?)
              ON CONFLICT (guild_id)
              DO UPDATE SET value=?;
            """
            db.cursor.execute(query, (guild.id, value, value))
            db.commit()
            db.close()

    def get(self, guild):
        if guild is None:
            return self.default_value
        return self.__data.get(guild.id, self.default_value)
