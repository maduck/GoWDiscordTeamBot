import json
import os
from config import CONFIG


class GameAssets:
    @staticmethod
    def load(filename):
        path = os.path.join(CONFIG.get('game_assets'), filename)
        with open(path, encoding='utf8') as f:
            return json.load(f)

    @staticmethod
    def path(filename):
        return os.path.join(CONFIG.get('game_assets'), filename)
