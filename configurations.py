import os
from collections import ChainMap

import hjson as json


class Configurations:
    DEFAULTS_FILE = 'settings_default.json'
    CONFIG_FILE = 'settings.json'

    def __init__(self):
        with open(self.DEFAULTS_FILE) as f:
            self.defaults = json.load(f)
        self.raw_config = {}
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE) as f:
                self.raw_config = json.load(f)
        self.config = ChainMap(self.raw_config, self.defaults)

    def get(self, key, default=None):
        return self.config.get(key, default)


CONFIG = Configurations()
