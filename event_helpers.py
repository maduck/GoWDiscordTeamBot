from game_constants import TROOP_RARITIES


def extract_name(raw_data):
    if 'Name' in raw_data:
        return {lang[:2]: name for lang, name in raw_data['Name'].items()}
    return {}


def extract_lore(raw_data):
    if 'Lore' in raw_data:
        return {lang[:2]: lore for lang, lore in raw_data['Lore'].items()}
    return {}


def roles_translation(roles):
    return [f'[TROOP_ROLE_{role.upper()}]' for role in roles]


def extract_currencies(raw_data):
    if 'CurrencyData' not in raw_data:
        return []
    return [
        {
            'icon': f'Liveeventscurrencies_{currency["Icon"]}_full',
            'value': currency['Value'],
            'name': {
                lang[:2]: translation
                for lang, translation in currency['Name'].items()
            },
        }
        for currency in raw_data['CurrencyData']
    ]


def transform_battle(battle):
    return {
        'ids': battle.get('TeamRules', {}).get('TroopIds', []),
        'names': {lang[:2]: translation for lang, translation in
                  battle['Name'].items()} if 'Name' in battle else {},
        'icon': f'Liveevents/Liveeventslocationicons_{battle["Icon"]}_full.png' if 'Icon' in battle else '',
        'rarity': TROOP_RARITIES[battle['Color']] if 'Color' in battle else '',
        'raw_rarity': battle.get('Color'),
    }


def get_first_battles(raw_data):
    battles = []
    for battle in raw_data.get('BattleArray', []):
        if 'Name' not in battle:
            continue

        battles.append({
            'name': battle['Name']['en_US'],
            'rarity': TROOP_RARITIES[battle.get('Color', 0)],
            'icon': battle.get('Icon', ''),
        })
    return battles
