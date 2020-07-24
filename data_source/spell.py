class Spell:
    def __init__(self):
        self.id = None
        self.name = None
        self.description = None
        self.cost = None
        self.amount = None
        self.multiplier = None
        self.boost = None

    def from_json(self, data):
        pass
