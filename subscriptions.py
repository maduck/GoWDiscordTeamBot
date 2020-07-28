import json
import os
import threading


class Subscriptions:
    SUBSCRIPTION_CONFIG_FILE = 'subscriptions.json'

    def __init__(self):
        self.subscriptions = None
        self.load_subscriptions()

    def save_subscriptions(self):
        lock = threading.Lock()
        with lock:
            with open(self.SUBSCRIPTION_CONFIG_FILE, 'w') as f:
                json.dump(self.subscriptions, f, sort_keys=True, indent=2)

    def load_subscriptions(self):
        if not os.path.exists(self.SUBSCRIPTION_CONFIG_FILE):
            return
        lock = threading.Lock()
        with lock:
            with open(self.SUBSCRIPTION_CONFIG_FILE) as f:
                self.subscriptions = json.load(f)

    @staticmethod
    def get_subscription_id(guild, channel):
        return f'{guild.id}-{channel.id}'

    @staticmethod
    def get_subscription(guild, channel):
        subscription_id = Subscriptions.get_subscription_id(guild, channel)
        subscription = {
            'guild_name': guild.name,
            'guild_id': guild.id,
            'channel_id': channel.id,
            'channel_name': channel.name,
        }
        return subscription_id, subscription

    def add(self, guild, channel):
        s_id, subscription = self.get_subscription(guild, channel)
        if s_id in self.subscriptions:
            self.subscriptions[s_id]['pc'] = True
        else:
            self.subscriptions[s_id] = subscription
        self.save_subscriptions()

    def remove(self, guild, channel):
        s_id, subscription = self.get_subscription(guild, channel)
        if self.is_subscribed(guild, channel):
            self.subscriptions[s_id]['pc'] = False
            self.subscriptions[s_id]['switch'] = False
            self.save_subscriptions()

    def is_subscribed(self, guild, channel):
        subscription = self.get_subscription_id(guild, channel)
        return subscription in self.subscriptions

    def __len__(self):
        return len(self.subscriptions)

    def __iter__(self):
        yield from self.subscriptions

    def __getitem__(self, index):
        return self.subscriptions[index]
