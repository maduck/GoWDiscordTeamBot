import asyncio

from models import DB


class Subscriptions:
    SUBSCRIPTION_CONFIG_FILE = 'subscriptions.json'

    def __init__(self):
        self._subscriptions = {}
        self.load_subscriptions()

    def load_subscriptions(self):
        db = DB()
        result = db.cursor.execute('SELECT * FROM Subscription;')
        subscriptions = result.fetchall()
        self._subscriptions = {f'{s["guild_id"]}-{s["channel_id"]}': {
            'guild_id': s['guild_id'],
            'guild_name': s['guild'],
            'channel_id': s['channel_id'],
            'channel_name': s['channel'],
            'pc': bool(s['pc']),
            'switch': bool(s['switch'])
        }
            for s in subscriptions}
        db.close()

    @staticmethod
    def get_subscription_id(guild, channel):
        return f'{guild.id}-{channel.id}'

    @staticmethod
    def get_subscription(guild, channel, platform=''):
        subscription_id = Subscriptions.get_subscription_id(guild, channel)
        subscription = {
            'guild_name': guild.name,
            'guild_id': guild.id,
            'channel_id': channel.id,
            'channel_name': channel.name,
            platform.lower(): True,
        }
        return subscription_id, subscription

    async def add(self, guild, channel, platform):
        s_id, subscription = self.get_subscription(guild, channel, platform)
        if s_id in self._subscriptions:
            self._subscriptions[s_id][platform.lower()] = True
        else:
            self._subscriptions[s_id] = subscription
        s = self._subscriptions[s_id]
        lock = asyncio.Lock()
        async with lock:
            db = DB()
            db.cursor.execute('REPLACE INTO Subscription (channel_id, guild_id, guild, channel, pc, switch) '
                              'VALUES (?, ?, ?, ?, ?, ?)',
                              (s['channel_id'],
                               s['guild_id'],
                               s['guild_name'],
                               s['channel_name'],
                               s.get('pc', False),
                               s.get('switch', False),
                               ))
            db.commit()
            db.close()

    async def remove(self, guild, channel):
        s_id, subscription = self.get_subscription(guild, channel)
        if self.is_subscribed(guild, channel):
            del self._subscriptions[s_id]
        lock = asyncio.Lock()
        async with lock:
            db = DB()
            db.cursor.execute('DELETE FROM Subscription WHERE channel_id = ?', (subscription['channel_id'],))
            db.commit()
            db.close()

    def is_subscribed(self, guild, channel):
        subscription_id = self.get_subscription_id(guild, channel)
        if subscription_id in self._subscriptions:
            return self._subscriptions[subscription_id]
        return False

    def __len__(self):
        return len(self._subscriptions)

    def __iter__(self):
        yield from self._subscriptions.values()
