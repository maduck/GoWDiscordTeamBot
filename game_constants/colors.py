import discord

RARITY_COLORS = {
    'Common': (255, 254, 255),
    'Uncommon': (84, 168, 31),
    'Rare': (32, 113, 254),
    'UltraRare': (150, 54, 232),
    'Epic': (246, 161, 32),
    'Legendary': (19, 227, 246),
    'Doomed': (186, 0, 0),
    'Mythic': (19, 227, 246),

}

CAMPAIGN_COLORS = {
    '[MEDAL_LEVEL_0]': discord.Color.from_rgb(164, 73, 32),
    '[MEDAL_LEVEL_1]': discord.Color.from_rgb(159, 159, 159),
    '[MEDAL_LEVEL_2]': discord.Color.from_rgb(238, 191, 15),
}

# public enum GemColor
COLORS = list(
    {
        0: 'blue',
        1: 'green',
        2: 'red',
        3: 'yellow',
        4: 'purple',
        5: 'brown',
        6: 'skull',
        7: 'doomskull',
        8: 'block',
        9: 'uberdoomskull',
        10: 'lycanthropy',
        11: 'bluemanapotion',
        12: 'greenmanapotion',
        13: 'redmanapotion',
        14: 'yellowmanapotion',
        15: 'purplemanapotion',
        16: 'brownmanapotion',
        17: 'wildcard2',
        18: 'wildcard3',
        19: 'wildcard4',
        20: 'burning',
        21: 'elementalstar',
        22: 'freeze',
        23: 'wish',
        24: 'lightdarkstar',
        25: 'cursed',
        26: 'goodgargoyle',
        27: 'badgargoyle',
        28: 'web',
        29: 'entangle',
        30: 'barrier',
        31: 'bomb',
        32: 'giantblue',
        33: 'giantgreen',
        34: 'giantred',
        35: 'giantyellow',
        36: 'giantpurple',
        37: 'giantbrown',
        38: 'dragonblue',
        39: 'dragongreen',
        40: 'dragonred',
        41: 'dragonyellow',
        42: 'dragonpurple',
        43: 'dragonbrown',
        44: 'spirit',
        45: 'stun',
        46: 'feariefire',
        47: 'deathmark',
        48: 'booty',
        49: 'basegemtypes',
        50: 'lootbronze',
        51: 'lootsilver',
        52: 'lootgold',
        53: 'lootbag',
        54: 'lootchest0',
        55: 'lootchest1',
        56: 'lootchest2',
        57: 'lootsafe',
    }.values())
