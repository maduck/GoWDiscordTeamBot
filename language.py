import json
import os
import threading


class Language:
    LANGUAGE_CONFIG_FILE = 'languages.json'

    def __init__(self, default_language):
        self.default_language = default_language
        self.__languages = {}
        self.load_languages()

    def load_languages(self):
        if not os.path.exists(self.LANGUAGE_CONFIG_FILE):
            return
        lock = threading.Lock()
        with lock:
            with open(self.LANGUAGE_CONFIG_FILE) as f:
                self.__languages = json.load(f)

    def save_languages(self):
        lock = threading.Lock()
        with lock:
            with open(self.LANGUAGE_CONFIG_FILE, 'w') as f:
                json.dump(self.__languages, f, sort_keys=True, indent=2)

    def set(self, guild, language):
        self.__languages[guild.id] = language
        self.save_languages()

    def get(self, guild):
        if guild is None:
            return self.default_language
        return self.__languages.get(guild.id, self.default_language)
