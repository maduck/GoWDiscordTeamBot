import discord

COLORS = ('blue', 'green', 'red', 'yellow', 'purple', 'brown', 'skull')

TROOP_RARITIES = (
    'Common',
    'Uncommon',
    'Rare',
    'UltraRare',
    'Epic',
    'Mythic',
    'Doomed'
)
WEAPON_RARITIES = (
    'Common',
    'Uncommon',
    'Rare',
    'UltraRare',
    'Epic',
    'Mythic',
    'Doomed'
)
RARITY_COLORS = {
    'Common': (255, 254, 255),
    'Uncommon': (84, 168, 31),
    'Rare': (32, 113, 254),
    'UltraRare': (150, 54, 232),
    'Epic': (246, 161, 32),
    'Legendary': (19, 227, 246),
    'Mythic': (19, 227, 246),
    'Doomed': (186, 0, 0),
}
CAMPAIGN_COLORS = {
    'Bronze': discord.Color.from_rgb(164, 73, 32),
    'Silver': discord.Color.from_rgb(159, 159, 159),
    'Gold': discord.Color.from_rgb(238, 191, 15),
}
EVENT_TYPES = {
    0: '[GUILD_WARS]',
    1: '[RAIDBOSS]',
    2: '[INVASION]',
    3: '[VAULT]',
    4: '[BOUNTY]',
    5: '[PETRESCUE]',
    6: '[CLASS_EVENT]',
    7: '[DELVE_EVENT]',
    8: '[TOWER_OF_DOOM]',
    9: '[HIJACK]',
    10: '[WEEKLY_EVENT]',
    11: '[CAMPAIGN]',
    12: '[ARENA]',
}
SOULFORGE_ALWAYS_AVAILABLE = [
    6428,  # Xathenos
    6529,  # Zuul'Got
    6919,  # Enraged Kurandara
    1104,  # Eye of Xathenos
    1176,  # Heart of Xathenos
    1177,  # Soul of Xathenos
    1111,  # Shattered Blade
    1112,  # Broken Guard
    1175,  # Dawnstone
    1113,  # Dawnbringer
    1374,  # Duskbringer
]
