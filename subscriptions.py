import json
import os
import threading


class Subscriptions:
    SUBSCRIPTION_CONFIG_FILE = 'subscriptions.json'

    def __init__(self):
        self.subscriptions = []
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
            self.deduplicate()

    def deduplicate(self):
        subscriptions = self.subscriptions.copy()
        self.subscriptions = []
        [self.subscriptions.append(s) for s in subscriptions if s not in self.subscriptions]
        if len(subscriptions) != len(self.subscriptions):
            self.save_subscriptions()

    @staticmethod
    def get_subscription_from_message(message):
        return {
            'guild_name': message.guild.name,
            'guild_id': message.guild.id,
            'channel_id': message.channel.id,
            'channel_name': message.channel.name,
        }

    def add(self, message):
        subscription = self.get_subscription_from_message(message)
        if not self.is_subscribed():
            self.subscriptions.append(subscription)
        self.save_subscriptions()

    def remove(self, message):
        subscription = self.get_subscription_from_message(message)
        if self.is_subscribed(message):
            self.subscriptions.remove(subscription)
            self.save_subscriptions()

    def is_subscribed(self, message):
        subscription = self.get_subscription_from_message(message)
        return subscription in self.subscriptions

    def __len__(self):
        return len(self.subscriptions)

    def __iter__(self):
        yield from self.subscriptions

    def __getitem__(self, index):
        return self.subscriptions[index]
