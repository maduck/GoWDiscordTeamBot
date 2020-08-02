import json
import os
import threading


class Prefix:
    PREFIX_CONFIG_FILE = 'prefixes.json'

    def __init__(self, default_prefix):
        self.default_prefix = default_prefix
        self.__prefixes = {}
        self.load_prefixes()

    def load_prefixes(self):
        if not os.path.exists(self.PREFIX_CONFIG_FILE):
            return
        lock = threading.Lock()
        with lock:
            with open(self.PREFIX_CONFIG_FILE) as f:
                self.__prefixes = json.load(f)

    def save_prefixes(self):
        lock = threading.Lock()
        with lock:
            with open(self.PREFIX_CONFIG_FILE, 'w') as f:
                json.dump(self.__prefixes, f, sort_keys=True, indent=2)

    def set(self, guild, prefix):
        self.__prefixes[str(guild.id)] = prefix
        self.save_prefixes()

    def get(self, guild):
        if guild is None:
            return self.default_prefix
        return self.__prefixes.get(guild.id, self.default_prefix)
