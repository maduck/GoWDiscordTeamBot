import asyncio
import re
from enum import Enum

import aiohttp

from models.pet_rescue_config import PetRescueConfig
from translations import LANGUAGES


class OptionType(Enum):
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8


STANDARD_OPTIONS = {
    'search_term': {
        'name': 'search_term',
        'description': 'case insensitive search or numeric id',
        'type': OptionType.STRING.value,
        'required': True,
        'choices': [],
    },
    'lang': {
        'name': 'lang',
        'description': 'language',
        'type': OptionType.STRING.value,
        'required': False,
        'choices': [{'name': v, 'value': k} for k, v in LANGUAGES.items() if k not in ('ru', 'cn')],
    },
    'shortened': {
        'name': 'shortened',
        'description': 'less data on output',
        'type': OptionType.BOOLEAN.value,
        'required': False,
    },
    'lengthened': {
        'name': 'lengthened',
        'description': 'more data on output',
        'type': OptionType.BOOLEAN.value,
        'required': False,
    },
}

LANG_PATTERN = r'(?P<lang>' + '|'.join(LANGUAGES) + ')?'
DEFAULT_PATTERN = f'^{LANG_PATTERN}(?P<shortened>-)?(?P<prefix>.)'
LENGTHENED_PATTERN = f'^{LANG_PATTERN}' + r'((?P<shortened>-)|(?P<lengthened>\+))?(?P<prefix>.)'

SEARCH_PATTERN = DEFAULT_PATTERN + '{0} #?(?P<search_term>.*)$'
MATCH_OPTIONS = re.IGNORECASE | re.MULTILINE
NO_QUOTE = r'^([^>].*?)??'
COMMAND_REGISTRY = [
    {
        'function': 'about',
        'pattern': re.compile(f'{DEFAULT_PATTERN}about$', MATCH_OPTIONS),
        'description': 'Shows general information about the bot',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'current_event',
        'pattern': re.compile(
            f'{LENGTHENED_PATTERN}(ce|current_event)$', MATCH_OPTIONS
        ),
        'description': 'Shows current event details',
        'options': [
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
            STANDARD_OPTIONS['lengthened'],
        ],
    },
    {
        'function': 'active_gems',
        'pattern': re.compile(f'{DEFAULT_PATTERN}active_gems$', MATCH_OPTIONS),
        'description': 'Shows active gem events',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'heroic_gems',
        'pattern': re.compile(f'{DEFAULT_PATTERN}heroic_gems$', MATCH_OPTIONS),
        'description': 'Shows all possible heroic gems',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'server_status',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}server_status$', MATCH_OPTIONS
        ),
        'description': 'Show Gems of War server status',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'stats',
        'pattern': re.compile(f'{DEFAULT_PATTERN}stats$', MATCH_OPTIONS),
    },
    {
        'function': 'adventures',
        'pattern': re.compile(f'{DEFAULT_PATTERN}adventures?$', MATCH_OPTIONS),
        'description': 'Shows today\'s adventure board',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'drop_rates',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}drop_(rate|chance)s?$', MATCH_OPTIONS
        ),
        'description': 'Chest drop chances',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'troop',
        'pattern': re.compile(
            SEARCH_PATTERN.format('tr(oop)?'), MATCH_OPTIONS
        ),
        'description': 'Search troops',
        'options': [
            STANDARD_OPTIONS['search_term'],
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'trait',
        'pattern': re.compile(SEARCH_PATTERN.format('trait'), MATCH_OPTIONS),
        'description': 'Search traits',
        'options': [
            STANDARD_OPTIONS['search_term'],
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'weapon',
        'pattern': re.compile(SEARCH_PATTERN.format('weapon'), MATCH_OPTIONS),
        'description': 'Search weapons',
        'options': [
            STANDARD_OPTIONS['search_term'],
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'affix',
        'pattern': re.compile(SEARCH_PATTERN.format('affix'), MATCH_OPTIONS),
        'description': 'Search weapon affixes',
        'options': [
            STANDARD_OPTIONS['search_term'],
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'kingdom_summary',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}kingdom summary$', MATCH_OPTIONS
        ),
        'description': 'Show all kingdoms in a table',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'faction_summary',
        'pattern': re.compile(f'{DEFAULT_PATTERN}factions$', MATCH_OPTIONS),
        'description': 'Show all factions and their colours',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'kingdom',
        'pattern': re.compile(SEARCH_PATTERN.format('kingdom'), MATCH_OPTIONS),
        'description': 'Search kingdoms',
        'options': [
            STANDARD_OPTIONS['search_term'],
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'faction',
        'pattern': re.compile(SEARCH_PATTERN.format('faction'), MATCH_OPTIONS),
        'description': 'Search factions',
        'options': [
            STANDARD_OPTIONS['search_term'],
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'show_pet_rescue_config',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}(pr|rp|pet rescue) config$', MATCH_OPTIONS
        ),
        'description': 'Shows the current channel\'s pet rescue configuration',
    },
    {
        'function': 'tools',
        'pattern': re.compile(f'{DEFAULT_PATTERN}tools$', MATCH_OPTIONS),
        'description': 'Show Gems of War related tools',
    },
    {
        'function': 'communities',
        'pattern': re.compile(f'{DEFAULT_PATTERN}communities$', MATCH_OPTIONS),
        'description': 'Show Gems of War related communities',
    },
    {
        'function': 'weekly_summary',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}(ws|weekly_summary)$', MATCH_OPTIONS
        ),
        'description': 'Shows a weekly summary',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'effects',
        'pattern': re.compile(f'{DEFAULT_PATTERN}effects$', MATCH_OPTIONS),
        'description': 'Shows all possible spell effects',
    },
    {
        'function': 'class_level',
        'pattern': re.compile(
            DEFAULT_PATTERN
            + r'class_level( ((?P<from>\d{1,3})( ?- ?))?(?P<to>\d{1,3}))$'
        ),
        'description': 'Calculate XP to level a class',
        'options': [
            {
                'name': 'to',
                'description': 'Target Level',
                'type': OptionType.INTEGER.value,
                'required': True,
                'min_value': 0,
                'max_value': 100,
            },
            {
                'name': 'from',
                'description': 'Starting Level',
                'type': OptionType.INTEGER.value,
                'required': False,
                'min_value': 0,
                'max_value': 100,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'set_pet_rescue_config',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}(pr|pet rescue) config (?P<key>[_a-zA-Z]+)([ =]+)(?P<value>.*)',
            MATCH_OPTIONS,
        ),
        'description': 'Configures a pet rescues for this channel',
        'options': [
            {
                'name': 'key',
                'description': 'Setting key to configure',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [
                    {'name': k, 'value': k}
                    for k in PetRescueConfig.DEFAULT_CONFIG.keys()
                ],
            },
            {
                'name': 'value',
                'description': 'Value to set the key to',
                'type': OptionType.STRING.value,
                'required': True,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'pet_rescue',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}(pr|pet rescue) (?P<search_term>.+?)'
            f'( (?P<time_left>[0-9]+)( ?m(ins?)?)?)?( (?P<mention><?@.+))?$',
            MATCH_OPTIONS,
        ),
        'description': 'Starts a pet rescue countdown and notifies everyone.',
        'options': [
            STANDARD_OPTIONS['search_term'],
            {
                'name': 'time_left',
                'description': 'time left for rescue, max 59 minutes',
                'type': OptionType.INTEGER.value,
                'required': False,
                'min_value': 0,
                'max_value': 59,
            },
            {
                'name': 'mention',
                'description': 'person or role to mention, defaults to `@everyone`',
                'type': OptionType.STRING.value,
                'required': False,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'pet_rescue_stats',
        'pattern': re.compile(f'{DEFAULT_PATTERN}pet_rescue_stats', MATCH_OPTIONS),
        'description': 'Show pets available in pet rescues',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'pet',
        'pattern': re.compile(SEARCH_PATTERN.format('pet'), MATCH_OPTIONS),
        'description': 'Search pets',
        'options': [
            STANDARD_OPTIONS['search_term'],
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'class_summary',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}class summary$', MATCH_OPTIONS
        ),
        'description': 'Show a summary table of all classes',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'class_',
        'pattern': re.compile(SEARCH_PATTERN.format('class'), MATCH_OPTIONS),
        'description': 'Search classes',
        'options': [
            STANDARD_OPTIONS['search_term'],
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'talent',
        'pattern': re.compile(
            SEARCH_PATTERN.format('talent(tree)?'), MATCH_OPTIONS
        ),
        'description': 'Search class talents',
        'options': [
            STANDARD_OPTIONS['search_term'],
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'talents',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}talent(tree)?s', MATCH_OPTIONS
        ),
        'description': 'Show all class talents',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'traitstones',
        'pattern': re.compile(
            SEARCH_PATTERN.format('traitstone'), MATCH_OPTIONS
        ),
        'description': 'Search traitstones',
        'options': [
            STANDARD_OPTIONS['search_term'],
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'event_kingdoms',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}events?[_ ]kingdoms?$', MATCH_OPTIONS
        ),
        'description': 'Show upcoming weekly event kingdoms',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'events',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}(spoilers? )?events?( (?P<filter>.*))?$',
            MATCH_OPTIONS,
        ),
        'description': 'Show upcoming events',
        'options': [
            {
                'name': 'filter',
                'description': 'case insensitive filter for events',
                'type': OptionType.STRING.value,
                'required': False,
                'choices': [],
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'spoilers',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}spoilers?( (?P<filter>(weapon|pet|kingdom|troop))s?)?$',
            MATCH_OPTIONS,
        ),
        'description': 'Show upcoming releases',
        'options': [
            {
                'name': 'filter',
                'description': 'case insensitive filter for spoilers',
                'type': OptionType.STRING.value,
                'required': False,
                'choices': [
                    {'name': 'Weapons', 'value': 'weapon'},
                    {'name': 'Pets', 'value': 'pet'},
                    {'name': 'Kingdoms', 'value': 'kingdom'},
                    {'name': 'Troops', 'value': 'troop'},
                ],
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'help',
        'pattern': re.compile(f'{DEFAULT_PATTERN}help$', MATCH_OPTIONS),
        'description': 'Shows bot help',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'quickhelp',
        'pattern': re.compile(f'{DEFAULT_PATTERN}quickhelp$', MATCH_OPTIONS),
        'description': 'Shows shorter bot reference help',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'show_prefix',
        'pattern': re.compile(f'{DEFAULT_PATTERN}prefix$', MATCH_OPTIONS),
    },
    {
        'function': 'change_prefix',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}prefix (?P<new_prefix>.+)$', MATCH_OPTIONS
        ),
    },
    {
        'function': 'show_tower_help',
        'pattern': re.compile(f'{DEFAULT_PATTERN}towerhelp$', MATCH_OPTIONS),
        'description': 'Shows the tower specific help',
    },
    {
        'function': 'show_tower_config',
        'pattern': re.compile(f'{DEFAULT_PATTERN}towerconfig$', MATCH_OPTIONS),
        'description': 'Shows the current server\'s tower config',
    },
    {
        'function': 'set_tower_config_alias',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}towerconfig (?P<category>(rooms|scrolls)) (?P<field>[^ ]+) (?P<values>.+)$',
            MATCH_OPTIONS,
        ),
        'description': 'Sets a tower configuration alias',
        'options': [
            {
                'name': 'category',
                'description': 'Category',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [
                    {'name': 'Rooms', 'value': 'rooms'},
                    {'name': 'Scrolls', 'value': 'scrolls'},
                ],
            },
            {
                'name': 'field',
                'description': 'Field',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [],
            },
            {
                'name': 'values',
                'description': 'Values',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [],
            },
        ],
    },
    {
        'function': 'set_tower_config_option',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}towerconfig (?P<option>(short|hide)) (?P<value>.+)$',
            MATCH_OPTIONS,
        ),
        'description': 'Sets a tower configuration option',
        'options': [
            {
                'name': 'option',
                'description': 'Option',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [
                    {'name': 'Short', 'value': 'short'},
                    {'name': 'Hide', 'value': 'hide'},
                ],
            },
            {
                'name': 'value',
                'description': 'Value',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [],
            },
        ],
    },
    {
        'function': 'reset_tower_config',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}towerconfig reset$', MATCH_OPTIONS
        ),
    },
    {
        'function': 'import_tower_from_taran',
        'pattern': re.compile(
            DEFAULT_PATTERN + 'tower taran (?P<map_name>[a-zA-Z0-9]{1,20})$',
            MATCH_OPTIONS,
        ),
        'options': [
            {
                'name': 'map_name',
                'description': 'map name as entered in taransworld.com',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [],
            },
        ],
        'description': 'Imports a tower map from Taran\'s World',
    },
    {
        'function': 'show_tower_data',
        'pattern': re.compile(
            DEFAULT_PATTERN + r'tower( (?P<range>\d+-\d+))?$', MATCH_OPTIONS
        ),
        'description': 'Shows the current Tower of Doom floors.',
        'options': [
            {
                'name': 'range',
                'description': 'Provide range, format: x-y',
                'type': OptionType.STRING.value,
                'required': False,
                'choices': [],
            },
            STANDARD_OPTIONS['shortened'],
        ],
    },
    {
        'function': 'clear_tower_data',
        'pattern': re.compile(f'{DEFAULT_PATTERN}towerclear$', MATCH_OPTIONS),
        'description': 'Clears the tower data for the current server',
    },
    {
        'function': 'edit_tower_single',
        'pattern': re.compile(
            f'^{LANG_PATTERN}(?P<prefix>.)tower (?P<floor>[^ ]+) (?P<room>[^ ]+) (?P<scroll>[^ ]+)$',
            MATCH_OPTIONS,
        ),
        'options': [
            {
                'name': 'floor',
                'description': 'Tower floor',
                'type': OptionType.INTEGER.value,
                'required': True,
                'choices': [],
            },
            {
                'name': 'room',
                'description': 'Tower room',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [],
            },
            {
                'name': 'scroll',
                'description': 'Scroll',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [],
            },
        ],
    },
    {
        'function': 'edit_tower_floor',
        'pattern': re.compile(
            (
                    f'^{LANG_PATTERN}'
                    + r'(?P<prefix>.)tower (?P<floor>\d+) (?P<scroll_ii>[^ ]+) (?P<scroll_iii>[^ ]+) '
                      r'(?P<scroll_iv>[^ ]+) (?P<scroll_v>[^ ]+) ?(?P<scroll_vi>[^ ]+)?$'
            ),
            MATCH_OPTIONS,
        ),
        'description': 'Edit a whole floor for Tower of Doom',
        'options': [
            {
                'name': 'floor',
                'description': 'Tower floor',
                'type': OptionType.INTEGER.value,
                'required': True,
                'choices': [],
            },
            {
                'name': 'scroll_ii',
                'description': 'Scroll for room II',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [],
            },
            {
                'name': 'scroll_iii',
                'description': 'Scroll for room III',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [],
            },
            {
                'name': 'scroll_iv',
                'description': 'Scroll for room IV',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [],
            },
            {
                'name': 'scroll_v',
                'description': 'Scroll for room V',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [],
            },
            {
                'name': 'scroll_vi',
                'description': 'Scroll for room VI',
                'type': OptionType.STRING.value,
                'required': False,
                'choices': [],
            },
        ],
    },
    {
        'function': 'delete_bookmark',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}bookmark delete (?P<bookmark_id>[a-zA-Z0-9]+)$',
            MATCH_OPTIONS,
        ),
        'description': 'Deletes an existing bookmark',
        'options': [
            {
                'name': 'bookmark_id',
                'description': 'Bookmark ID',
                'type': OptionType.STRING.value,
                'required': True,
            },
        ],
    },
    {
        'function': 'create_bookmark',
        'pattern': re.compile(
            DEFAULT_PATTERN
            + r'bookmark (?P<description>[^,]+)? (\[(?P<team_code>(\d+,?){1,13})])$',
            MATCH_OPTIONS,
        ),
        'description': 'Create a new bookmark',
        'options': [
            {
                'name': 'description',
                'description': 'Description',
                'type': OptionType.STRING.value,
                'required': True,
            },
            {
                'name': 'team_code',
                'description': 'Team Code',
                'type': OptionType.STRING.value,
                'required': True,
            },
            STANDARD_OPTIONS['shortened'],
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'show_bookmark',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}bookmark (?P<bookmark_id>[a-zA-Z0-9]+)$',
            MATCH_OPTIONS,
        ),
        'description': 'Show an existing bookmark',
        'options': [
            {
                'name': 'bookmark_id',
                'description': 'Bookmark ID',
                'type': OptionType.STRING.value,
                'required': True,
            },
            STANDARD_OPTIONS['shortened'],
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'show_my_bookmarks',
        'pattern': re.compile(f'{DEFAULT_PATTERN}bookmarks$', MATCH_OPTIONS),
        'description': 'Show my own bookmarks',
    },
    {
        'function': 'team_code',
        # TODO adapt to something more strict, maybe this?
        # \[(?P<weapon_troops>([167]\d{3},?)+){1,4}(?P<banner>3\d{3},?)?(?P<talents>([0-3]{1},?){7})?(?P<class>\d{5})?\]
        'pattern': re.compile(
            NO_QUOTE
            + LANG_PATTERN
            + r'((?P<shortened>-)|(?P<lengthened>\+))?\[(?P<team_code>(\d+,?){1,13})].*',
            MATCH_OPTIONS | re.DOTALL,
        ),
        'description': 'display team with code copied from the game',
        'options': [
            {
                'name': 'team_code',
                'description': 'team code',
                'type': OptionType.STRING.value,
                'required': True,
            },
            {
                'name': 'title',
                'description': 'What is the team for? E.g. "World Event". Limit: 256 characters.',
                'type': OptionType.STRING.value,
                'required': False,
            },
            STANDARD_OPTIONS['lang'],
            STANDARD_OPTIONS['shortened'],
            STANDARD_OPTIONS['lengthened'],
        ],
    },
    {
        'function': 'news_subscribe',
        'pattern': re.compile(
            r'^(?P<prefix>.)news subscribe( (?P<platform>pc|switch))?$',
            MATCH_OPTIONS,
        ),
        'description': 'Subscribe this channel to news',
        'options': [
            {
                'name': 'platform',
                'description': 'Platform to display news for',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [
                    {'name': 'PC / Mobile', 'value': 'pc'},
                    {'name': 'Nintendo Switch', 'value': 'switch'},
                ],
            }
        ],
    },
    {
        'function': 'news_unsubscribe',
        'pattern': re.compile(
            r'^(?P<prefix>.)news unsubscribe$', MATCH_OPTIONS
        ),
        'description': 'Unsubscribe this channel from all news postings.',
    },
    {
        'function': 'news_status',
        'pattern': re.compile(r'^(?P<prefix>.)news( status)?$', MATCH_OPTIONS),
        'description': 'Check whether this channel is subscribed to any news postings.',
    },
    {
        'function': 'waffles',
        'pattern': re.compile(
            DEFAULT_PATTERN + r'waffles?( #?(?P<waffle_no>[0-9]{1,2}))?$',
            MATCH_OPTIONS,
        ),
        'description': 'Easter egg command.',
        'options': [
            {
                'name': 'waffle_no',
                'description': 'Waffle number',
                'type': OptionType.INTEGER.value,
                'required': False,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'memes',
        'pattern': re.compile(
            DEFAULT_PATTERN + r'memes?( #?(?P<meme_no>[0-9]{1,3}))?$',
            MATCH_OPTIONS,
        ),
        'description': 'Easter egg command #2.',
        'options': [
            {
                'name': 'meme_no',
                'description': 'Meme number',
                'type': OptionType.INTEGER.value,
                'required': False,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'burgers',
        'pattern': re.compile(
            DEFAULT_PATTERN + r'burgers?( #?(?P<burger_no>[0-9]{1,2}))?$',
            MATCH_OPTIONS,
        ),
        'description': 'Easter egg command #3.',
        'options': [
            {
                'name': 'burger_no',
                'description': 'Burger number',
                'type': OptionType.INTEGER.value,
                'required': False,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'show_languages',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}lang(uages?)?$', MATCH_OPTIONS
        ),
        'description': 'Show all languages supported by the bot.',
    },
    {
        'function': 'change_language',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}lang(uages?)? (?P<new_language>.+)$',
            MATCH_OPTIONS,
        ),
        'description': 'Change the standard language for this server.',
        'options': [
            {
                'name': 'new_language',
                'description': 'new language for this server',
                'type': OptionType.STRING.value,
                'required': True,
                'choices': [
                    {'name': v, 'value': k}
                    for k, v in LANGUAGES.items()
                    if k not in ('ru', 'cn')
                ],
            }
        ],
    },
    {
        'function': 'campaign',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}campaign( (?P<tier>bronze|silver|gold))?$',
            MATCH_OPTIONS,
        ),
        'description': "Show current week's campaign tasks",
        'options': [
            {
                'name': 'tier',
                'description': 'Tier filter for campaign tasks',
                'type': OptionType.STRING.value,
                'required': False,
                'choices': [
                    {'name': 'Bronze', 'value': 'bronze'},
                    {'name': 'Silver', 'value': 'silver'},
                    {'name': 'Gold', 'value': 'gold'},
                ],
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'reroll_tasks',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}reroll_tasks( (?P<tier>bronze|silver|gold))?$',
            MATCH_OPTIONS,
        ),
        'description': "Show campaign re-roll tasks",
        'options': [
            {
                'name': 'tier',
                'description': 'Tier filter for campaign re-roll tasks',
                'type': OptionType.STRING.value,
                'required': False,
                'choices': [
                    {'name': 'Bronze', 'value': 'bronze'},
                    {'name': 'Silver', 'value': 'silver'},
                    {'name': 'Gold', 'value': 'gold'},
                ],
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'color_kingdoms',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}color_kingdoms?$', MATCH_OPTIONS
        ),
        'description': 'Shows the best farming kingdom for each mana color',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'troop_type_kingdoms',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}troop_type_kingdoms?$', MATCH_OPTIONS
        ),
        'description': 'Shows the best farming kingdom for each troop type',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'banners',
        'pattern': re.compile(f'{DEFAULT_PATTERN}banners$', MATCH_OPTIONS),
        'description': 'Display all banners',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'warbands',
        'pattern': re.compile(f'{DEFAULT_PATTERN}warbands?$', MATCH_OPTIONS),
        'description': 'Shows all available Warband banners',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'soulforge',
        'pattern': re.compile(
            f'{LENGTHENED_PATTERN}(sf|soulforge)$', MATCH_OPTIONS
        ),
        'description': 'Show this week\'s craftable items in Soulforge',
        'options': [STANDARD_OPTIONS['lang'], STANDARD_OPTIONS['lengthened']],
    },
    {
        'function': 'summoning_stones',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}(summoning_stones|summons)$', MATCH_OPTIONS
        ),
        'description': 'Show this week\'s craftable summoning stones contents',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'streamers',
        'pattern': re.compile(f'{DEFAULT_PATTERN}streamers?$', MATCH_OPTIONS),
        'description': 'Show some Gems of War streamers',
    },
    {
        'function': 'levels',
        'pattern': re.compile(f'{DEFAULT_PATTERN}levels$', MATCH_OPTIONS),
        'description': 'Show the player\'s level progression bonuses',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'update_toplist',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}toplist update (?P<toplist_id>[a-zA-Z0-9]+) (?P<description>[^,]+)? (?P<items>(.+,?)+)$',
            MATCH_OPTIONS,
        ),
        'description': 'Overwrite an existing toplist',
        'options': [
            {
                'name': 'toplist_id',
                'description': 'Toplist ID',
                'type': OptionType.STRING.value,
                'required': True,
            },
            {
                'name': 'description',
                'description': 'Description',
                'type': OptionType.STRING.value,
                'required': True,
            },
            {
                'name': 'items',
                'description': 'Items (Weapons & Troops, comma separated)',
                'type': OptionType.STRING.value,
                'required': True,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'append_toplist',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}toplist append (?P<toplist_id>[a-zA-Z0-9]+) (?P<items>(.+,?)+)$',
            MATCH_OPTIONS,
        ),
        'description': 'Add item(s) to an existing toplist',
        'options': [
            {
                'name': 'toplist_id',
                'description': 'Toplist ID',
                'type': OptionType.STRING.value,
                'required': True,
            },
            {
                'name': 'items',
                'description': 'Items (Weapons & Troops, comma separated)',
                'type': OptionType.STRING.value,
                'required': True,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'delete_toplist',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}toplist delete (?P<toplist_id>[a-zA-Z0-9]+)$',
            MATCH_OPTIONS,
        ),
        'description': 'Deletes an existing toplist',
        'options': [
            {
                'name': 'toplist_id',
                'description': 'Toplist ID',
                'type': OptionType.STRING.value,
                'required': True,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'create_toplist',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}toplist (?P<description>[^,]+)? (?P<items>(.+,?)+)$',
            MATCH_OPTIONS,
        ),
        'description': 'Creates a new toplist',
        'options': [
            {
                'name': 'description',
                'description': 'Description',
                'type': OptionType.STRING.value,
                'required': True,
            },
            {
                'name': 'items',
                'description': 'Items (Weapons & Troops, comma separated)',
                'type': OptionType.STRING.value,
                'required': True,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'show_toplist',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}toplist (?P<toplist_id>[a-zA-Z0-9]+)$',
            MATCH_OPTIONS,
        ),
        'description': 'Show an existing toplist',
        'options': [
            {
                'name': 'toplist_id',
                'description': 'Toplist ID',
                'type': OptionType.STRING.value,
                'required': True,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'show_my_toplists',
        'pattern': re.compile(f'{DEFAULT_PATTERN}toplists$', MATCH_OPTIONS),
        'description': 'Show toplists created by you',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'show_permissions',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}permissions?$', MATCH_OPTIONS
        ),
        'description': 'Check and show missing permissions',
    },
    {
        'function': 'world_map',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}world_map( (?P<location>krystara|underworld))?',
            MATCH_OPTIONS,
        ),
        'description': 'Renders a world map',
        'options': [
            {
                'name': 'location',
                'description': 'Which map to render?',
                'type': OptionType.STRING.value,
                'required': False,
                'choices': [
                    {'name': 'Krystara (Default)', 'value': 'krystara'},
                    {'name': 'Underworld', 'value': 'underworld'},
                ],
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'soulforge_preview',
        'pattern': re.compile(
            DEFAULT_PATTERN + r'soulforge_preview (?P<search_term>.+?)( '
                              r'(?P<release_date>\d{1,2}-\d{1,2}))?(?P<switch>.?Switch)?$',
            MATCH_OPTIONS,
        ),
        'description': 'Generate a Soulforge Preview image',
        'options': [
            STANDARD_OPTIONS['search_term'],
            {
                'name': 'release_date',
                'description': 'Date of weapon release, format MONTH-DAY with two digits each (e.g. 12-25). '
                               'Defaults to next Monday.',
                'type': OptionType.STRING.value,
                'required': False,
            },
            {
                'name': 'switch',
                'description': 'Add Nintendo Switch logo',
                'type': OptionType.BOOLEAN.value,
                'required': False,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'storms',
        'pattern': re.compile(f'{DEFAULT_PATTERN}storms$', MATCH_OPTIONS),
        'description': 'Show all available storms',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'hoard_potions',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}hoard_potions$', MATCH_OPTIONS
        ),
        'description': 'Show potions for faction hoards',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'campaign_preview',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}campaign_preview(?P<switch> Switch)?( (?P<team_code>.*))?$',
            MATCH_OPTIONS,
        ),
        'description': 'Generate a Campaign Preview image',
        'options': [
            {
                'name': 'team_code',
                'description': 'Proposed team to solve campaign tasks',
                'type': OptionType.STRING.value,
                'required': False,
            },
            {
                'name': 'switch',
                'description': 'Add Nintendo Switch logo',
                'type': OptionType.BOOLEAN.value,
                'required': False,
            },
            STANDARD_OPTIONS['lang'],
        ],
    },
    {
        'function': 'search_guild',
        'pattern': re.compile(
            SEARCH_PATTERN.format('search_guild'), MATCH_OPTIONS
        ),
    },
    {
        'function': 'kick_guild',
        'pattern': re.compile(
            DEFAULT_PATTERN + r'kick_guild (?P<guild_id>\d+)', MATCH_OPTIONS
        ),
    },
    {
        'function': 'ban_guild',
        'pattern': re.compile(
            DEFAULT_PATTERN + r'ban_guild (?P<guild_id>\d+) (?P<reason>.+)$',
            MATCH_OPTIONS,
        ),
    },
    {
        'function': 'dungeon_traps',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}dungeon_traps?', MATCH_OPTIONS
        ),
        'options': [STANDARD_OPTIONS['lang']],
        'description': 'Show traps that occur in the daily Dungeon',
    },
    {
        'function': 'dungeon_altars',
        'pattern': re.compile(
            f'{DEFAULT_PATTERN}dungeon_altars?', MATCH_OPTIONS
        ),
        'options': [STANDARD_OPTIONS['lang']],
        'description': 'Show altars that occur in the daily Dungeon',
    },
    {
        'function': 'orbs',
        'pattern': re.compile(f'{DEFAULT_PATTERN}orbs$', MATCH_OPTIONS),
        'options': [STANDARD_OPTIONS['lang']],
        'description': 'Shows Orbs in the game',
    },
    {
        'function': 'medals',
        'pattern': re.compile(f'{DEFAULT_PATTERN}medals$', MATCH_OPTIONS),
        'options': [STANDARD_OPTIONS['lang']],
        'description': 'Shows Badges & Medals in the game',
    }
]

aliases = {
    'pet_rescue': 'pr',
    'team_code': 'tc',
}

for command in COMMAND_REGISTRY.copy():
    if command['function'] in aliases:
        new_command = command.copy()
        new_command['function'] = aliases[command['function']]
        new_command['description'] = f'Shorthand for /{command["function"]}'
        COMMAND_REGISTRY.append(new_command)


# taken from https://github.com/eunwoo1104/discord-py-slash-command
async def add_slash_command(bot_id,
                            bot_token: str,
                            guild_id,
                            cmd_name: str,
                            description: str,
                            options: list = None):
    """
    A coroutine that sends a slash command add request to Discord API.
    :param bot_id: User ID of the bot.
    :param bot_token: Token of the bot.
    :param guild_id: ID of the guild to add command. Pass `None` to add global command.
    :param cmd_name: Name of the command. Must be 3 or longer and 32 or shorter.
    :param description: Description of the command.
    :param options: List of the function.
    :return: JSON Response of the request.
    :raises: :class:`.error.RequestFailure` - Requesting to Discord API has failed.
    """
    url = f"https://discord.com/api/v8/applications/{bot_id}"
    url += f"/guilds/{guild_id}/commands" if guild_id else "/commands"
    base = {"name": cmd_name, "description": description, "options": options or []}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers={"Authorization": f"Bot {bot_token}"}, json=base) as resp:
            if resp.status == 429:
                _json = await resp.json()
                await asyncio.sleep(_json["retry_after"])
                return await add_slash_command(bot_id, bot_token, guild_id, cmd_name, description, options)
            if not 200 <= resp.status < 300:
                raise RuntimeError(resp.status, await resp.text())
            return await resp.json()


async def remove_slash_command(bot_id,
                               bot_token,
                               guild_id,
                               cmd_id):
    """
    A coroutine that sends a slash command remove request to Discord API.
    :param bot_id: User ID of the bot.
    :param bot_token: Token of the bot.
    :param guild_id: ID of the guild to remove command. Pass `None` to remove global command.
    :param cmd_id: ID of the command.
    :return: Response code of the request.
    :raises: :class:`.error.RequestFailure` - Requesting to Discord API has failed.
    """
    url = f"https://discord.com/api/v8/applications/{bot_id}"
    url += f"/guilds/{guild_id}/commands" if guild_id else "/commands"
    url += f"/{cmd_id}"
    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers={"Authorization": f"Bot {bot_token}"}) as resp:
            if resp.status == 429:
                _json = await resp.json()
                await asyncio.sleep(_json["retry_after"])
                return await remove_slash_command(bot_id, bot_token, guild_id, cmd_id)
            if not 200 <= resp.status < 300:
                raise RuntimeError(resp.status, await resp.text())
            return resp.status


async def get_all_commands(bot_id, bot_token, guild_id):
    """
    A coroutine that sends a slash command get request to Discord API.
    :param bot_id: User ID of the bot.
    :param bot_token: Token of the bot.
    :param guild_id: ID of the guild to get commands. Pass `None` to get all global commands.
    :return: JSON Response of the request.
    :raises: :class:`.error.RequestFailure` - Requesting to Discord API has failed.
    """
    url = f"https://discord.com/api/v8/applications/{bot_id}"
    url += f"/guilds/{guild_id}/commands" if guild_id else "/commands"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"Authorization": f"Bot {bot_token}"}) as resp:
            if resp.status == 429:
                _json = await resp.json()
                await asyncio.sleep(_json["retry_after"])
                return await get_all_commands(bot_id, bot_token, guild_id)
            if not 200 <= resp.status < 300:
                raise RuntimeError(resp.status, await resp.text())
            return await resp.json()
