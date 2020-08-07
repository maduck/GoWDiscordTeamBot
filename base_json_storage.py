import json
import os
import threading


class BaseGuildStorage:
    FILENAME = None

    def __init__(self, default_value):
        self.default_value = default_value
        self.__data = {}
        self.load()

    def load(self):
        if not os.path.exists(self.FILENAME):
            return
        lock = threading.Lock()
        with lock:
            with open(self.FILENAME) as f:
                self.__data = json.load(f)

    def save(self):
        lock = threading.Lock()
        with lock:
            with open(self.FILENAME, 'w') as f:
                json.dump(self.__data, f, sort_keys=True, indent=2)

    def set(self, guild, value):
        self.__data[str(guild.id)] = value
        self.save()

    def get(self, guild):
        if guild is None:
            return self.default_value
        return self.__data.get(str(guild.id), self.default_value)
