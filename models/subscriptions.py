import json
import os
import threading


class Subscriptions:
    SUBSCRIPTION_CONFIG_FILE = '../subscriptions.json'

    def __init__(self):
        self._subscriptions = {}
        self.load_subscriptions()

    def save_subscriptions(self):
        lock = threading.Lock()
        with lock:
            with open(self.SUBSCRIPTION_CONFIG_FILE, 'w') as f:
                json.dump(self._subscriptions, f, sort_keys=True, indent=2)

    def load_subscriptions(self):
        if not os.path.exists(self.SUBSCRIPTION_CONFIG_FILE):
            return
        lock = threading.Lock()
        with lock:
            with open(self.SUBSCRIPTION_CONFIG_FILE) as f:
                self._subscriptions = json.load(f)

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

    def add(self, guild, channel, platform):
        s_id, subscription = self.get_subscription(guild, channel, platform)
        if s_id in self._subscriptions:
            self._subscriptions[s_id][platform.lower()] = True
        else:
            self._subscriptions[s_id] = subscription
        self.save_subscriptions()

    def remove(self, guild, channel):
        s_id, subscription = self.get_subscription(guild, channel)
        if self.is_subscribed(guild, channel):
            del self._subscriptions[s_id]
            self.save_subscriptions()

    def is_subscribed(self, guild, channel):
        subscription_id = self.get_subscription_id(guild, channel)
        if subscription_id in self._subscriptions:
            subscription = self._subscriptions[subscription_id]
            return subscription
        return False

    def __len__(self):
        return len(self._subscriptions)

    def __iter__(self):
        yield from self._subscriptions.values()
