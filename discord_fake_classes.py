class FakeMessage:
    id = 0

    def __init__(self, author, guild, channel, content, interaction_id=None, interaction_token=None):
        self.author = author
        self.guild = guild
        self.channel = FakeChannel(channel)
        self.channel.recipient = author
        self.content = content
        self.interaction_id = interaction_id
        self.interaction_token = interaction_token


class FakeChannel:
    def __init__(self, channel):
        self.typing = FakeTyping
        self.channel = channel
        self.permissions_for = None
        if hasattr(channel, 'permissions_for'):
            self.permissions_for = channel.permissions_for
        self.recipient = None

    def send(self, *args, **kwargs):
        return self.channel.send(*args, **kwargs)

    @property
    def id(self):
        return self.channel.id

    @property
    def type(self):
        return self.channel.type

    @property
    def name(self):
        return self.channel.name

    def __str__(self) -> str:
        return str(self.channel)


class FakeTyping:
    async def __aenter__(self):
        """ mimics the async enter for Typing """
        pass

    async def __aexit__(self, type, value, traceback):
        """ mimics the async exit for Typing """
        pass
