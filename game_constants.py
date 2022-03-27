import enum

import discord

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
        32: 'basegemtypes',
        33: 'lootbronze',
        34: 'lootsilver',
        35: 'lootgold',
        36: 'lootbag',
        37: 'lootchest0',
        38: 'lootchest1',
        39: 'lootchest2',
        40: 'lootsafe',
    }.values())

# public enum TutorialStep
GEM_TUTORIAL_IDS = {
    'uberdoomskull': 3340,
    'lycanthropy': 3341,
    'bluemanapotion': 3342,
    'greenmanapotion': 3342,
    'redmanapotion': 3342,
    'yellowmanapotion': 3342,
    'purplemanapotion': 3342,
    'brownmanapotion': 3342,
    'wildcard2': 3343,
    'wildcard3': 3343,
    'wildcard4': 3343,
    'burning': 3344,
    'freeze': 3345,
    'elementalstar': 3346,
    'wish': 3347,
    'lightdarkstar': 3348,
    'cursed': 3349,
    'goodgargoyle': 3350,
    'badgargoyle': 3350,
    'web': 3351,
    'entangle': 3352,
    'barrier': 3353,
    'bomb': 3354,
    'lootgold': 99999,
}

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

# public enum EventType
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
    6997,  # Leonis Tower
    7033,  # Hatir Ascendent
    7034,  # Scroll Reborn
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

COST_TYPES = (
    'Cash',
    '[GEMS]',
    '[GLORY]',
    '[TROOPHELP_COUNT0]',
)


class RewardTypes(enum.IntEnum):
    Gems = 0
    Gold = 1
    Skin = 3
    Weapon = 4
    Troop = 5
    Souls = 6
    TreasureMaps = 8
    Bundle = 11
    Subscription = 12
    GoldKeys = 13
    GloryKeys = 14
    GemKeys = 15
    EventKeys = 16
    VIPKeys = 17
    TraitStones = 18
    GuildSeals = 19
    GuildKeysForAll = 20
    GuildKeys = 21
    Race = 22
    PathToGlory1 = 23
    PathToGlory2 = 24
    GrowthPack = 25
    Diamonds = 26
    Shards = 27
    Jewels = 28
    RingOfWonder = 29
    Glory = 30
    LiveEventPoolTroop = 31
    LiveEventTroop = 32
    Pet = 33
    PetFood = 34
    Orbs = 35
    LiveEventEnergy = 36
    VaultKeys = 37
    Ingots = 38
    ChampionXP = 39
    ChaosShards = 40
    PathToGlory3 = 41
    PathToGlory4 = 42
    Gift = 43
    LiveEventScroll = 44
    ForgeScroll = 45
    ChatPortrait = 46
    ChatTitle = 47
    ChatEmoji = 48
    ChatSticker = 49
    LiveEventPotion = 50
    Deed = 51
    Medal = 52
    ExploreMythStones = 53
    Writ = 54
    GnomeBait = 55
    ExploreBoss = 56
    LiveEventCurrency = 57
    ElitePass = 58
    ElitePassPlus = 59
    ArtifactLevel = 60
    DeedBook = 61
    EpicVaultKeys = 62
    RandomTroop = 63
    ChampionLevelUp = 64
    ChampionTraitsUnlocked = 65
    DelveChestUpgrade = 66
    DelveAttempts = 67
    FactionRenown = 68
    LiveEventPoints = 69
