import asyncio
import re
from enum import Enum

import aiohttp

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
        'description': 'case insensitive search',
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
    }
}

LANG_PATTERN = r'(?P<lang>' + '|'.join(LANGUAGES) + ')?'
DEFAULT_PATTERN = '^' + LANG_PATTERN + '(?P<shortened>-)?(?P<prefix>.)'
SEARCH_PATTERN = DEFAULT_PATTERN + '{0} #?(?P<search_term>.*)$'
MATCH_OPTIONS = re.IGNORECASE | re.MULTILINE
COMMAND_REGISTRY = [
    {
        'function': 'about',
        'pattern': re.compile(DEFAULT_PATTERN + 'about$', MATCH_OPTIONS),
        'description': 'Shows general information about the bot',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'stats',
        'pattern': re.compile(DEFAULT_PATTERN + 'stats$', MATCH_OPTIONS),
    },
    {
        'function': 'troop',
        'pattern': re.compile(SEARCH_PATTERN.format('troop'), MATCH_OPTIONS),
        'description': 'Search troops',
        'options': [STANDARD_OPTIONS['search_term'], STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'trait',
        'pattern': re.compile(SEARCH_PATTERN.format('trait'), MATCH_OPTIONS),
        'description': 'Search traits',
        'options': [STANDARD_OPTIONS['search_term'], STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'weapon',
        'pattern': re.compile(SEARCH_PATTERN.format('weapon'), MATCH_OPTIONS),
        'description': 'Search weapons',
        'options': [STANDARD_OPTIONS['search_term'], STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'affix',
        'pattern': re.compile(SEARCH_PATTERN.format('affix'), MATCH_OPTIONS),
        'description': 'Search weapon affixes',
        'options': [STANDARD_OPTIONS['search_term'], STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'show_kingdom_summary',
        'pattern': re.compile(DEFAULT_PATTERN + 'kingdom summary$', MATCH_OPTIONS)
    },
    {
        'function': 'kingdom',
        'pattern': re.compile(SEARCH_PATTERN.format('(kingdom|faction)'), MATCH_OPTIONS),
        'description': 'Search kingdoms',
        'options': [STANDARD_OPTIONS['search_term'], STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'show_pet_rescue_config',
        'pattern': re.compile(DEFAULT_PATTERN + '(pr|pet rescue) config$', MATCH_OPTIONS)
    },
    {
        'function': 'set_pet_rescue_config',
        'pattern': re.compile(DEFAULT_PATTERN + '(pr|pet rescue) config (?P<key>[_a-zA-Z]+)([ =]+)(?P<value>.*)',
                              MATCH_OPTIONS)
    },
    {
        'function': 'pet_rescue',
        'pattern': re.compile(
            DEFAULT_PATTERN +
            '(pr|pet rescue) (?P<search_term>.+?)( (?P<time_left>[0-9]+)( ?min)?)?( (?P<mention><?@.+))?$',
            MATCH_OPTIONS),
        'description': 'Shows general information about the bot',
        'options': [STANDARD_OPTIONS['search_term'],
                    {
                        'name': 'time_left',
                        'description': 'time left for rescue, max 59 minutes',
                        'type': OptionType.INTEGER.value,
                        'required': False,
                    },
                    {
                        'name': 'mention',
                        'description': 'person or role to mention, defaults to `@everyone`',
                        'type': OptionType.STRING.value,
                        'required': False,
                    },
                    STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'pet',
        'pattern': re.compile(SEARCH_PATTERN.format('pet'), MATCH_OPTIONS),
        'description': 'Search pets',
        'options': [STANDARD_OPTIONS['search_term'], STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'show_class_summary',
        'pattern': re.compile(DEFAULT_PATTERN + 'class summary$', MATCH_OPTIONS)
    },
    {
        'function': 'class_',
        'pattern': re.compile(SEARCH_PATTERN.format('class'), MATCH_OPTIONS),
        'description': 'Search classes',
        'options': [STANDARD_OPTIONS['search_term'], STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'talent',
        'pattern': re.compile(SEARCH_PATTERN.format('talent'), MATCH_OPTIONS),
        'description': 'Search class talents',
        'options': [STANDARD_OPTIONS['search_term'], STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'traitstones',
        'pattern': re.compile(SEARCH_PATTERN.format('traitstone'), MATCH_OPTIONS),
        'description': 'Search traitstones',
        'options': [STANDARD_OPTIONS['search_term'], STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'show_event_kingdoms',
        'pattern': re.compile(DEFAULT_PATTERN + r'events? kingdoms?$', MATCH_OPTIONS)
    },
    {
        'function': 'events',
        'pattern': re.compile(DEFAULT_PATTERN + '(spoilers? )?events?( (?P<filter>.*))?$', MATCH_OPTIONS),
        'description': 'Show upcoming events',
        'options': [{
            'name': 'filter',
            'description': 'case insensitive filter for events',
            'type': OptionType.STRING.value,
            'required': False,
            'choices': [],
        },
            STANDARD_OPTIONS['lang'],
        ]
    },
    {
        'function': 'spoilers',
        'pattern': re.compile(DEFAULT_PATTERN + 'spoilers?( (?P<filter>(weapon|pet|kingdom|troop))s?)?$',
                              MATCH_OPTIONS),
        'description': 'Show upcoming releases',
        'options': [{
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
        }, STANDARD_OPTIONS['lang'],
        ]
    },
    {
        'function': 'help',
        'pattern': re.compile(DEFAULT_PATTERN + 'help$', MATCH_OPTIONS),
        'description': 'Shows bot help',
        'options': [STANDARD_OPTIONS['lang']],

    },
    {
        'function': 'quickhelp',
        'pattern': re.compile(DEFAULT_PATTERN + 'quickhelp$', MATCH_OPTIONS),
        'description': 'Shows shorter bot reference help',
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'show_prefix',
        'pattern': re.compile(DEFAULT_PATTERN + 'prefix$', MATCH_OPTIONS)
    },
    {
        'function': 'change_prefix',
        'pattern': re.compile(DEFAULT_PATTERN + 'prefix (?P<new_prefix>.+)$', MATCH_OPTIONS)
    },
    {
        'function': 'show_tower_help',
        'pattern': re.compile(DEFAULT_PATTERN + 'towerhelp$', MATCH_OPTIONS)
    },
    {
        'function': 'show_tower_config',
        'pattern': re.compile(DEFAULT_PATTERN + 'towerconfig$', MATCH_OPTIONS)
    },
    {
        'function': 'set_tower_config_alias',
        'pattern': re.compile(DEFAULT_PATTERN + 'towerconfig (?P<category>(rooms|scrolls)) (?P<field>[^ ]+)'
                                                r' (?P<values>.+)$', MATCH_OPTIONS)
    },
    {
        'function': 'set_tower_config_option',
        'pattern': re.compile(DEFAULT_PATTERN + 'towerconfig (?P<option>(short|hide))'
                                                r' (?P<value>.+)$', MATCH_OPTIONS)
    },
    {
        'function': 'reset_tower_config',
        'pattern': re.compile(DEFAULT_PATTERN + 'towerconfig reset$', MATCH_OPTIONS)
    },
    {
        'function': 'show_tower_data',
        'pattern': re.compile(DEFAULT_PATTERN + r'tower( (?P<range>\d+-\d+))?$', MATCH_OPTIONS)
    },
    {
        'function': 'clear_tower_data',
        'pattern': re.compile(DEFAULT_PATTERN + 'towerclear$', MATCH_OPTIONS)
    },
    {
        'function': 'edit_tower_single',
        'pattern': re.compile(
            r'^' + LANG_PATTERN + r'(?P<prefix>.)tower (?P<floor>[^ ]+) (?P<room>[^ ]+) (?P<scroll>[^ ]+)$',
            MATCH_OPTIONS)
    },
    {
        'function': 'edit_tower_floor',
        'pattern': re.compile(
            r'^' + LANG_PATTERN + r'(?P<prefix>.)tower (?P<floor>\d+) (?P<scroll_ii>[^ ]+) (?P<scroll_iii>[^ ]+) '
                                  r'(?P<scroll_iv>[^ ]+) (?P<scroll_v>[^ ]+) ?(?P<scroll_vi>[^ ]+)?$',
            MATCH_OPTIONS)
    },
    {
        'function': 'handle_team_code',
        'pattern': re.compile(
            r'^([^>].*)??' + LANG_PATTERN + r'(?P<shortened>-)?\[(?P<team_code>(\d+,?){1,13})].*',
            MATCH_OPTIONS | re.DOTALL)
    },
    {
        'function': 'news_subscribe',
        'pattern': re.compile(r'^(?P<prefix>.)news subscribe( (?P<platform>pc|switch))?$', MATCH_OPTIONS)
    },
    {
        'function': 'news_unsubscribe',
        'pattern': re.compile(r'^(?P<prefix>.)news unsubscribe$', MATCH_OPTIONS)
    },
    {
        'function': 'news_status',
        'pattern': re.compile(r'^(?P<prefix>.)news( status)?$', MATCH_OPTIONS)
    },
    {
        'function': 'waffles',
        'pattern': re.compile(r'^(?P<prefix>.)waffles$', MATCH_OPTIONS),
        'description': "Easteregg command. Don't use.",
    },
    {
        'function': 'show_languages',
        'pattern': re.compile(DEFAULT_PATTERN + 'lang(uages?)?$', MATCH_OPTIONS)
    },
    {
        'function': 'change_language',
        'pattern': re.compile(DEFAULT_PATTERN + 'lang(uages?)? (?P<new_language>.+)$', MATCH_OPTIONS)
    },
    {
        'function': 'campaign',
        'pattern': re.compile(DEFAULT_PATTERN + 'campaign( (?P<tier>bronze|silver|gold))?$', MATCH_OPTIONS),
        'description': "Show current week's campaign tasks",
        'options': [{
            'name': 'tier',
            'description': 'Tier filter for campaign tasks',
            'type': OptionType.STRING.value,
            'required': False,
            'choices': [
                {'name': 'Bronze', 'value': 'bronze'},
                {'name': 'Silver', 'value': 'silver'},
                {'name': 'Gold', 'value': 'gold'},
            ],
        }, STANDARD_OPTIONS['lang'],
        ]
    },
    {
        'function': 'soulforge',
        'pattern': re.compile(DEFAULT_PATTERN + 'soulforge$', MATCH_OPTIONS),
        'description': "Show this week's craftable items in Soulforge",
        'options': [STANDARD_OPTIONS['lang']],
    },
    {
        'function': 'show_levels',
        'pattern': re.compile(DEFAULT_PATTERN + 'levels$', MATCH_OPTIONS)
    },
    {
        'function': 'update_toplist',
        'pattern': re.compile(
            DEFAULT_PATTERN + r'toplist update (?P<_id>[a-zA-Z0-9]+) (?P<description>.+)? (?P<items>(.+,?)+)$',
            MATCH_OPTIONS)
    },
    {
        'function': 'append_toplist',
        'pattern': re.compile(
            DEFAULT_PATTERN + r'toplist append (?P<_id>[a-zA-Z0-9]+) (?P<items>(.+,?)+)$',
            MATCH_OPTIONS)
    },
    {
        'function': 'delete_toplist',
        'pattern': re.compile(
            DEFAULT_PATTERN + r'toplist delete (?P<_id>[a-zA-Z0-9]+)$', MATCH_OPTIONS)
    },
    {
        'function': 'create_toplist',
        'pattern': re.compile(DEFAULT_PATTERN + r'toplist (?P<description>.+)? (?P<items>(.+,?)+)$',
                              MATCH_OPTIONS)
    },
    {
        'function': 'show_toplist',
        'pattern': re.compile(DEFAULT_PATTERN + r'toplist (?P<toplist_id>[a-zA-Z0-9]+)$', MATCH_OPTIONS)
    },
    {
        'function': 'show_my_toplists',
        'pattern': re.compile(DEFAULT_PATTERN + r'toplists$', MATCH_OPTIONS)
    },
    {
        'function': 'show_permissions',
        'pattern': re.compile(DEFAULT_PATTERN + r'permissions?$', MATCH_OPTIONS)
    }
]


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
    url += "/commands" if not guild_id else f"/guilds/{guild_id}/commands"
    base = {
        "name": cmd_name,
        "description": description,
        "options": options if options else []
    }

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
    url += "/commands" if not guild_id else f"/guilds/{guild_id}/commands"
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
    url += "/commands" if not guild_id else f"/guilds/{guild_id}/commands"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"Authorization": f"Bot {bot_token}"}) as resp:
            if resp.status == 429:
                _json = await resp.json()
                await asyncio.sleep(_json["retry_after"])
                return await get_all_commands(bot_id, bot_token, guild_id)
            if not 200 <= resp.status < 300:
                raise RuntimeError(resp.status, await resp.text())
            return await resp.json()
