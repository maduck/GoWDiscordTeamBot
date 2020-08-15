import aiosqlite


class DB:
    def __init__(self, filename):
        self.filename = filename
        self.conn = None
        self.cursor = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.filename)
        self.cursor = await self.conn.cursor()

    async def disconnect(self):
        await self.cursor.close()
        await self.conn.close()
