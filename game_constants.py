import discord

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
        25: 'curse',
        26: 'basegemtypes',
        27: 'lootbronze',
        28: 'lootsilver',
        29: 'lootgold',
        30: 'lootbag',
        31: 'lootchest0',
        32: 'lootchest1',
        33: 'lootchest2',
        34: 'lootsafe',
    }.values())

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
    'Doomed': (186, 0, 0),
    'Mythic': (19, 227, 246),

}
CAMPAIGN_COLORS = {
    '[MEDAL_LEVEL_0]': discord.Color.from_rgb(164, 73, 32),
    '[MEDAL_LEVEL_1]': discord.Color.from_rgb(159, 159, 159),
    '[MEDAL_LEVEL_2]': discord.Color.from_rgb(238, 191, 15),
}
TASK_SKIP_COSTS = {
    '[MEDAL_LEVEL_0]': 50,
    '[MEDAL_LEVEL_1]': 100,
    '[MEDAL_LEVEL_2]': 150,
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
    13: '[JOURNEY]',
    14: '[KINGDOM_PASS]',
}
SOULFORGE_ALWAYS_AVAILABLE = [
    6428,  # Xathenos
    6529,  # Zuul'Goth
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
SOULFORGE_REQUIREMENTS = {
    'UltraRare': {
        'jewels': 300,
        'Runes_JewelDiamond_full.png': 75,
        'Runes_Rune39_full.png': 3,
        'Commonrewards_icon_soul_small_full.png': 3000,
    },
    'Epic': {
        'jewels': 600,
        'Runes_JewelDiamond_full.png': 300,
        'Runes_Rune39_full.png': 3,
        'Commonrewards_icon_soul_small_full.png': 15000,
    },
    'Mythic': {
        'jewels': 0,
        'Runes_JewelDiamond_full.png': 200,
        'Runes_Rune39_full.png': 3,
        'Commonrewards_icon_soul_small_full.png': 1000000,
    },
    'Doomed': {
        'jewels': 2200,
        'Runes_JewelDiamond_full.png': 900,
        'Runes_Rune39_full.png': 10,
        'Commonrewards_icon_soul_small_full.png': 60000,
    }
}
UNDERWORLD_SOULFORGE_REQUIREMENTS = {
    'Epic': {
        'jewels': 400,
        'Runes_JewelDiamond_full.png': 200,
        'Runes_Rune39_full.png': 2,
        'Commonrewards_icon_soul_small_full.png': 10000,
    },
}
