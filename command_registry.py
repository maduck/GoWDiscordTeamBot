import re

from translations import LANGUAGES

LANG_PATTERN = r'(?P<lang>' + '|'.join(LANGUAGES) + ')?'
DEFAULT_PATTERN = '^' + LANG_PATTERN + '(?P<shortened>-)?(?P<prefix>.)'
SEARCH_PATTERN = DEFAULT_PATTERN + '{0} #?(?P<search_term>.*)$'
MATCH_OPTIONS = re.IGNORECASE | re.MULTILINE
COMMAND_REGISTRY = [
    {
        'function': 'show_version',
        'pattern': re.compile(DEFAULT_PATTERN + 'version$', MATCH_OPTIONS)
    },
    {
        'function': 'show_uptime',
        'pattern': re.compile(DEFAULT_PATTERN + 'uptime$', MATCH_OPTIONS)
    },
    {
        'function': 'handle_troop_search',
        'pattern': re.compile(SEARCH_PATTERN.format('troop'), MATCH_OPTIONS)
    },
    {
        'function': 'handle_weapon_search',
        'pattern': re.compile(SEARCH_PATTERN.format('weapon'), MATCH_OPTIONS)
    },
    {
        'function': 'show_kingdom_summary',
        'pattern': re.compile(DEFAULT_PATTERN + 'kingdom summary$', MATCH_OPTIONS)
    },
    {
        'function': 'handle_kingdom_search',
        'pattern': re.compile(SEARCH_PATTERN.format('kingdom'), MATCH_OPTIONS)
    },
    {
        'function': 'handle_pet_search',
        'pattern': re.compile(SEARCH_PATTERN.format('pet'), MATCH_OPTIONS)
    },
    {
        'function': 'show_class_summary',
        'pattern': re.compile(DEFAULT_PATTERN + 'class summary$', MATCH_OPTIONS)
    },
    {
        'function': 'handle_class_search',
        'pattern': re.compile(SEARCH_PATTERN.format('class'), MATCH_OPTIONS)
    },
    {
        'function': 'handle_talent_search',
        'pattern': re.compile(SEARCH_PATTERN.format('talent'), MATCH_OPTIONS)
    },
    {
        'function': 'show_events',
        'pattern': re.compile(DEFAULT_PATTERN + '(spoilers? )?events?$', MATCH_OPTIONS)
    },
    {
        'function': 'show_spoilers',
        'pattern': re.compile(DEFAULT_PATTERN + 'spoilers?( (?P<_filter>(weapon|pet|kingdom|troop))s?)?',
                              MATCH_OPTIONS)
    },
    {
        'function': 'show_help',
        'pattern': re.compile(DEFAULT_PATTERN + 'help$', MATCH_OPTIONS)
    },
    {
        'function': 'show_quickhelp',
        'pattern': re.compile(DEFAULT_PATTERN + 'quickhelp$', MATCH_OPTIONS)
    },
    {
        'function': 'show_invite_link',
        'pattern': re.compile(DEFAULT_PATTERN + 'invite$', MATCH_OPTIONS)
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
        'pattern': re.compile(DEFAULT_PATTERN + 'tower$', MATCH_OPTIONS)
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
            r'^' + LANG_PATTERN + r'(?P<prefix>.)tower (?P<floor>[^ ]+) (?P<scroll_ii>[^ ]+) (?P<scroll_iii>[^ ]+) '
                                  r'(?P<scroll_iv>[^ ]+) (?P<scroll_v>[^ ]+) ?(?P<scroll_vi>[^ ]+)?$',
            MATCH_OPTIONS)
    },
    {
        'function': 'handle_team_code',
        'pattern': re.compile(
            r'^([^>]*?)?' + LANG_PATTERN + r'(?P<shortened>-)?\[(?P<team_code>(\d+,?){1,13})].*',
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
        'pattern': re.compile(r'^(?P<prefix>.)waffles$', MATCH_OPTIONS)
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
        'function': 'show_campaign_tasks',
        'pattern': re.compile(DEFAULT_PATTERN + 'campaign( (?P<tier>bronze|silver|gold))?$', MATCH_OPTIONS)
    },
    {
        'function': 'show_soulforge',
        'pattern': re.compile(DEFAULT_PATTERN + 'soulforge', MATCH_OPTIONS)
    }
]
