import datetime
import math

import discord
from jinja2 import Environment, FileSystemLoader

from configurations import CONFIG
from game_constants import RARITY_COLORS
from search import _
from util import chunks, flatten


class Views:
    WHITE = discord.Color.from_rgb(254, 254, 254)
    BLACK = discord.Color.from_rgb(0, 0, 0)
    RED = discord.Color.from_rgb(255, 0, 0)

    def __init__(self, emojis):
        self.my_emojis = emojis
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))

    def banner_colors(self, banner):
        return [f'{self.my_emojis.get(d[0], f":{d[0]}:")}{abs(d[1]) * f"{d[1]:+d}"[0]}' for d in banner['colors']]

    def render_embed(self, embed, template_name, **kwargs):
        self.jinja_env.filters['emoji'] = self.my_emojis.get
        self.jinja_env.filters['banner_colors'] = self.banner_colors
        self.jinja_env.globals.update({
            'emoji': self.my_emojis.get,
            'flatten': flatten
        })

        template = self.jinja_env.get_template(template_name)
        content = template.render(**kwargs)

        for i, splitted in enumerate(content.split('<T>')):
            if i == 0:
                embed.description = splitted
            else:
                title_end = splitted.index('</T>')
                inline = splitted.startswith('inline')
                embed.add_field(
                    name=splitted[inline * len('inline'):title_end],
                    value=splitted[title_end + 4:],
                    inline=inline)
        return embed

    def render_help(self, prefix, lang):
        title = f'garyatrics.com bot {_("[HELP]", lang)}'
        e = discord.Embed(title=title, color=self.WHITE)
        self.render_embed(e, f'help/help-{lang}.jinja', prefix=prefix)
        e.add_field(name=f'__{_("[SUPPORT]", lang)}__:', value='<https://discord.gg/XWs7x3cFTU>')
        return e

    def render_weapon(self, weapon, shortened):
        rarity_color = RARITY_COLORS.get(weapon['raw_rarity'], RARITY_COLORS['Mythic'])
        color = discord.Color.from_rgb(*rarity_color)
        e = discord.Embed(title='Weapon search found one exact match', color=color)
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Spells/Cards_{weapon["spell_id"]}_full.png'
        e.set_thumbnail(url=thumbnail_url)
        if shortened:
            return self.render_embed(e, 'weapon_shortened.jinja', weapon=weapon)

        if 'release_date' in weapon:
            e.set_footer(text='Release date')
            e.timestamp = weapon["release_date"]
        return self.render_embed(e, 'weapon.jinja', weapon=weapon)

    def render_affix(self, affix, shortened):
        e = discord.Embed(title='Affix search found one exact match', color=self.WHITE)
        affix['weapons'] = [f'{w["name"]} `#{w["id"]}`' for w in affix['weapons']]
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Ingots/Ingots_AnvilIcon_full.png'
        e.set_thumbnail(url=thumbnail_url)
        return self.render_embed(e, 'affix.jinja', affix=affix)

    def render_pet(self, pet, shortened=False):
        e = discord.Embed(title='Pet search found one exact match', color=self.WHITE)
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Pets/Cards_{pet["filename"]}_full.png'
        e.set_thumbnail(url=thumbnail_url)
        if shortened:
            return self.render_embed(e, 'pet_shortened.jinja', pet=pet)

        if 'release_date' in pet:
            e.set_footer(text='Release date')
            e.timestamp = pet["release_date"]
        return self.render_embed(e, 'pet.jinja', pet=pet)

    def render_troop(self, troop, shortened):
        rarity_color = RARITY_COLORS.get(troop['raw_rarity'], RARITY_COLORS['Mythic'])
        if 'Boss' in troop['raw_types']:
            rarity_color = RARITY_COLORS['Doomed']
        e = discord.Embed(title='Troop search found one exact match', color=discord.Color.from_rgb(*rarity_color))
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Troops/Cards_{troop["filename"]}_full.png'
        e.set_thumbnail(url=thumbnail_url)
        if shortened:
            return self.render_embed(e, 'troop_shortened.jinja', troop=troop)

        if 'release_date' in troop:
            e.set_footer(text='Release date')
            e.timestamp = troop["release_date"]
        return self.render_embed(e, 'troop.jinja', troop=troop)

    def render_traitstone(self, traitstone, shortened):
        e = discord.Embed(color=self.WHITE)
        e.title = traitstone['name']
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Runes_Rune{traitstone["id"]:02d}_full.png'
        e.set_thumbnail(url=thumbnail_url)
        troops = ['{0} ({1})'.format(*troop) for troop in traitstone['troops']]
        chunk_size = 50
        troop_chunks = [', '.join(chunk) for chunk in chunks(troops, chunk_size)][:6]
        class_list = ['{0} ({1})'.format(*_class) for _class in traitstone['classes']]
        classes = self.trim_text_to_length(", ".join(sorted(class_list)), 900, ',', ', ...')
        if shortened:
            troop_chunks = None
            classes = None
        kingdom_list = [k for k in traitstone['kingdoms']]
        kingdoms = self.trim_text_to_length(", ".join(sorted(kingdom_list)), 900, ',', ', ...')

        return self.render_embed(e, 'traitstone.jinja',
                                 traitstone=traitstone,
                                 troops=troops,
                                 troop_chunks=troop_chunks,
                                 chunk_size=chunk_size,
                                 classes=classes,
                                 kingdoms=kingdoms)

    def render_talent(self, tree, shortened):
        e = discord.Embed(color=self.WHITE)
        if shortened:
            e.title = tree["name"]
            return self.render_embed(e, 'talent_shortened.jinja', tree=tree)

        e.title = 'Talent search found one exact match'
        return self.render_embed(e, 'talent.jinja', tree=tree)

    def render_team(self, team, author, shortened, team_code=None, title=None):
        color = discord.Color.from_rgb(*RARITY_COLORS['Mythic'])
        e = discord.Embed(color=color)
        if team['banner']:
            thumbnail_url = f'{CONFIG.get("graphics_url")}/Banners/Banners_{team["banner"]["filename"]}_full.png'
            e.set_thumbnail(url=thumbnail_url)

        if shortened:
            troops = [f'{t[1]}' for t in team['troops']]
            e.title = ', '.join(troops)
            return self.render_embed(e, 'team_shortened.jinja', team=team)

        e.title = f"{author} team"
        if title:
            e.title = title
        return self.render_embed(e, 'team.jinja', team=team)

    def render_kingdom(self, kingdom, shortened):
        e = discord.Embed(title='Kingdom search found one exact match', color=self.WHITE)
        underworld = 'underworld' if kingdom['underworld'] else ''
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Maplocations{underworld}_{kingdom["filename"]}_full.png'
        e.set_thumbnail(url=thumbnail_url)

        if shortened:
            return self.render_embed(e, 'kingdom_shortened.jinja', kingdom=kingdom)
        return self.render_embed(e, 'kingdom.jinja', kingdom=kingdom)

    def render_trait(self, trait, shortened):
        e = discord.Embed(title='Trait search found one exact match', color=self.WHITE)
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Troopcardall_Traits/{trait["image"]}_full.png'
        e.set_thumbnail(url=thumbnail_url)
        trait['thumbnail'] = thumbnail_url
        return self.render_embed(e, 'trait.jinja', trait=trait)

    def render_class(self, _class, shortened):
        e = discord.Embed(title='Class search found one exact match', color=self.WHITE)
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Classes_{_class["code"]}_full.png'
        e.set_thumbnail(url=thumbnail_url)
        if shortened:
            return self.render_embed(e, 'class_shortened.jinja', _class=_class)

        return self.render_embed(e, 'class.jinja', _class=_class)

    @staticmethod
    def trim_text_to_length(text, limit, break_character='\n', indicator=''):
        input_text = f'{text}{break_character}'
        trimmed_text = input_text[:input_text[:limit].rfind(break_character)]
        if trimmed_text != text:
            trimmed_text += indicator
        return trimmed_text

    @classmethod
    def trim_text_lines_to_length(cls, lines, limit, break_character='\n'):
        if not lines:
            return lines
        input_text = break_character.join(lines) + break_character
        trimmed_text = cls.trim_text_to_length(input_text, limit)
        return trimmed_text.split(break_character)

    @classmethod
    def trim_news_to_length(cls, text, link, max_length=900):
        trimmed_text = cls.trim_text_to_length(text, max_length)
        if len(trimmed_text) > max_length:
            trimmed_text = cls.trim_text_to_length(text, max_length, break_character=' ')
        read_more = ''
        if len(trimmed_text) != len(text):
            read_more = f'[...]\n\n[Read full news article]({link}).'
        result = f'{trimmed_text}{read_more}'
        return result

    def render_events(self, events, _filter, lang):
        e = discord.Embed(title=_('[EVENTS]', lang), color=self.WHITE)
        message_lines = []
        last_event_date = events[0]['start']
        for event in events:
            if event['start'] > last_event_date and event['start'].weekday() == 0 and not _filter:
                message_lines.append('')
            last_event_date = event['start']
            end = f'- {event["end"].strftime("%b %d")} '
            if event['end'] == event['start'] + datetime.timedelta(days=1):
                end = ''
            this_line = f'{event["start"].strftime("%b %d")} ' \
                        f'{end}' \
                        f'{event["type"]}' \
                        f'{":" if event["extra_info"] else ""} ' \
                        f'{event["extra_info"]}'
            if not _filter or _filter.lower() in this_line.lower():
                message_lines.append(this_line)
        message_lines = self.trim_text_lines_to_length(message_lines, 894)
        if not message_lines:
            message_lines = [_('[QUEST9052_ENDCONV_0]', lang).replace('&& ', '\n')]
        message_lines = ['```'] + message_lines + ['```']
        e.add_field(name=_('[CALENDAR]', lang), value='\n'.join(message_lines))
        return e

    def render_event_kingdoms(self, events):
        e = discord.Embed(title='Upcoming Event Kingdoms', color=self.WHITE)
        message_lines = ['```']
        for event in events:
            message_lines.append(f'{event["start"].strftime("%b %d")} - '
                                 f'{event["end"].strftime("%b %d")}  '
                                 f'{event["kingdom"]}')
        message_lines = self.trim_text_lines_to_length(message_lines, 900)
        message_lines.append('```')
        e.add_field(name='Spoilers', value='\n'.join(message_lines))
        e.set_footer(text='* Projected from troop spoilers.')
        return e

    def render_levels(self, levels):
        e = discord.Embed(title='Level progression overview', color=self.WHITE)
        return self.render_embed(e, 'levels.jinja', levels=levels)

    def render_toplist(self, toplist):
        if not toplist:
            e = discord.Embed(title='Toplist not found.', color=self.BLACK)
            return e
        e = discord.Embed(title=f'Toplist ID `{toplist["id"]}` by {toplist["author_name"]}', color=self.WHITE)
        e.set_footer(text='Last modified')
        e.timestamp = toplist['created']
        chunk_size = 4
        item_chunks = chunks(toplist['items'], chunk_size)
        for i, chunk in enumerate(item_chunks, start=1):
            formatted_chunk = [
                f'**{chunk_size * (i - 1) + j}. {self.my_emojis.get(item["color_code"])} {item["name"]}** '
                f'({item["kingdom"]} {item["rarity"]}) '
                f'{item["spell"]["description"]}'
                for j, item in enumerate(chunk, start=1)]
            chunk_message = '\n'.join(formatted_chunk)
            title = f'__{(i - 1) * chunk_size + 1}...{i * chunk_size}__'
            if i == 1:
                title = toplist['description']
            e.add_field(name=title, value=chunk_message, inline=False)

        return e

    def render_my_toplists(self, toplists, author_name):
        e = discord.Embed(title='Toplists', color=self.WHITE)
        message_lines = []
        for toplist in toplists:
            message_lines.append(f'**{toplist["id"]}** {toplist["description"]}')
        if not message_lines:
            message_lines = ['No toplists created yet.']
        e.add_field(name=f'Overview for {author_name}', value='\n'.join(message_lines), inline=False)
        return e

    def render_pet_rescue(self, rescue):
        lang = rescue.lang
        e = self.render_pet(rescue.pet, lang)
        e.title = _('[PETRESCUE]', lang)
        time_left = _('[PETRESCUE_ENDS_IN_HOURS]', lang).replace('%1', '00').replace('%2', f'{rescue.time_left:02d}')
        rescue_message = f'{_("[PETRESCUE_OVERVIEW_PETSUBTITLE]", lang)}\n{time_left}'
        e.add_field(name=_('[PETRESCUE_HELP_SHORT]', lang), value=rescue_message)
        return e

    def render_pet_rescue_config(self, config, lang):
        on = _('[ON]', lang)
        off = _('[OFF]', lang)

        pretty_display = {
            'mention': '**Who gets mentioned?** `mention =',
            'delete_pet': '**Deletion of the pet info** `delete_pet =',
            'delete_mention': '**Deletion of the mention** `delete_mention =',
            'delete_message': '**Deletion of the original request message¹** `delete_message =',
        }

        def translate_value(value):
            if value is False:
                return off
            elif value is True:
                return on
            return value

        answer = '\n'.join([f'{pretty_display[key]} {translate_value(value)}`' for key, value in config.items()])
        e = discord.Embed(title=_('[PETRESCUE]', lang), color=self.WHITE)
        e.add_field(name=_('[SETTINGS]', lang), value=answer)
        e.set_footer(text='¹ needs "Manage Messages" permission, or will react with ⛔ emoji.')
        return e

    def render_permissions(self, channel, permissions):
        e = discord.Embed(title=f'Channel Permissions for {channel}', color=self.WHITE)
        permission_lines = [f'{v} {k.replace("_", " ").title()}' for k, v in permissions.items()]
        e.add_field(name='__Checklist__', value='\n'.join(permission_lines))
        return e

    def render_quickhelp(self, prefix, lang, languages):
        e = discord.Embed(title='Quick Help', color=self.WHITE)
        return self.render_embed(e, f'help/quickhelp-{lang}.jinja', prefix=prefix, languages='|'.join(languages))

    def render_tower_help(self, prefix, lang):
        title = f'{_("[TOWER_OF_DOOM]", lang)} {_("[HELP]", lang)}'
        e = discord.Embed(title=title, color=self.WHITE)
        return self.render_embed(e, f'help/tower_of_doom-{lang}.jinja', prefix=prefix)

    def render_news(self, article):
        e = discord.Embed(title=article['title'], color=self.WHITE, url=article['url'])
        content = self.transform_news_article(article['content'], article['url'])
        self.enrich_author(e, article['author'])
        for title, text in content.items():
            e.add_field(name=title, value=text, inline=False)
        result = [e]
        for i, image_url in enumerate(article['images']):
            if i >= len(result):
                e = discord.Embed(type='image', color=self.WHITE)
                e.set_image(url=image_url)
                result.append(e)
            else:
                e = result[i]
                e.set_image(url=image_url)
        return result

    def transform_news_article(self, content, url=''):
        # FIXME: the following works around bug reported in:
        #  https://community.gemsofwar.com/t/news-contain-invalid-html-tags-reported/67756/
        #  Needs to be removed as soon as the bug is resolved.
        content = content.replace('_Scoring_', '\n_Scoring_\n')
        text_lines = content.split('\n')
        result = {}
        field = []
        field_title = 'News'
        for line in text_lines:
            if line.startswith('_') and line.endswith('_'):
                if field:
                    result[field_title] = self.trim_news_to_length('\n'.join(field), link=url)
                    field = []
                field_title = line
            else:
                field.append(line)
        result[field_title] = self.trim_news_to_length('\n'.join(field), link=url)
        return result

    def render_color_kingdoms(self, kingdoms, lang):
        top_n = _('[TOP_N]', lang)
        mana_color_troop = _('[COLOR_TROOP]', lang)
        top_kingdoms = top_n.replace('%1%', _('[KINGDOMS]', lang))
        title = f'{top_kingdoms} ({mana_color_troop})'
        e = discord.Embed(title=title, color=self.WHITE)
        for color_code, kingdom in kingdoms.items():
            color = self.my_emojis.get(color_code, color_code)
            name = f'{color} __{kingdom["name"]}__ ({kingdom["percentage"]:0.0%})'
            color_name = _(f'[GEM_{color_code.upper()}]', lang)
            troops_title = _('[N_TROOPS]', lang).replace('%1', color_name)
            value = f'**{_("[TOTAL_TROOPS]", lang)}**: {kingdom["total"]}\n' \
                    f'**{troops_title}**: {kingdom["fitting_troops"]}'
            e.add_field(name=name, value=value)
        return e

    def render_type_kingdoms(self, kingdoms, lang):
        top_n = _('[TOP_N]', lang)
        troop_type = _('[FILTER_TROOPTYPE]', lang)
        top_kingdoms = top_n.replace('%1%', _('[KINGDOMS]', lang))

        title = f'{top_kingdoms} ({troop_type})'
        e = discord.Embed(title=title, color=self.WHITE)

        half_size = math.ceil(len(kingdoms) / 2)
        chunked_kingdoms = chunks(kingdoms, half_size)
        for i, chunk in enumerate(chunked_kingdoms, start=0):
            chunk_title = _('[TROOP_TYPES]', lang)
            start = i * half_size + 1
            end = i * half_size + len(chunk)
            title = f'{chunk_title} {start:n} - {end:n}'
            field_lines = [
                f'{troop_type} __{kingdom["name"]}__ ({kingdom["percentage"]:0.0%})' for
                troop_type, kingdom in chunk]
            e.add_field(name=title, value='\n'.join(field_lines))
        return e

    def render_adventure_board(self, adventures, lang):
        highest_rarity = max([a['raw_rarity'] for a in adventures])
        color = list(RARITY_COLORS.values())[highest_rarity]
        e = discord.Embed(title=_('[ADVENTURE_BOARD]', lang), color=discord.Color.from_rgb(*color))

        for adventure in adventures:
            reward_emojis = [self.my_emojis.get(t.lower()[1:-1], '') for t in adventure['reward_types']]
            name = f'{"".join(reward_emojis)} __{adventure["name"]}__ ({adventure["rarity"]})'
            rewards = ', '.join([f'{v} {k}' for k, v in adventure['rewards'].items()])
            e.add_field(name=name, value=rewards, inline=False)
        now = datetime.datetime.utcnow()
        reset_time = now.replace(hour=7, minute=0, second=0, microsecond=0)
        time_left = reset_time + datetime.timedelta(hours=24) - now
        hours = time_left.seconds // 3600
        minutes = time_left.seconds // 60 - hours * 60
        footer = _('[DAILY_ADVENTURES_RESET_IN]', lang).replace('%1', str(hours)).replace('%2', str(minutes))
        e.set_footer(text=footer)
        return e

    def render_class_level(self, lower_level, upper_level, xp_required, speeds, lang):
        title = f'{_("[CHAMPION_LEVEL_N]", lang)}'.replace('%1', f'{lower_level} - {upper_level}')
        e = discord.Embed(title=title, color=self.WHITE)
        name = f'{_("[CHAMPION_LEVEL]", lang)} {_("[XP]", lang)}'
        xp = f'{xp_required} {_("[XP]", lang)}'
        e.add_field(name=name, value=xp)
        xp_speed = _('[N_MINUTE]', lang).replace('%1', f'{_("[XP]", lang)} / ')
        hours = _('[N_HOURS]', lang)
        for i, (xp_per_min, time) in enumerate(speeds.items()):
            name = _(f'[ANIMATION_SPEED_{i}]', lang)
            value = f'{xp_per_min} {xp_speed}: **{hours.replace("%1", time)}**'
            e.add_field(name=name, value=value, inline=False)
        e.set_footer(text=_('[CHAMPION_XP_INFO]', lang))
        return e

    def render_tools(self):
        e = discord.Embed(title='Community Tools', color=self.WHITE)
        return self.render_embed(e, 'tools.jinja')

    def render_my_bookmarks(self, bookmarks, display_name):
        e = discord.Embed(title='Bookmarks', color=self.WHITE)
        message_lines = []
        for bookmark in bookmarks:
            message_lines.append(f'**{bookmark["id"]}** {bookmark["description"]}')
        if not message_lines:
            message_lines = ['No bookmarks created yet.']
        e.add_field(name=f'Overview for {display_name}', value='\n'.join(message_lines), inline=False)
        return e

    @staticmethod
    def enrich_author(e, author):
        author_details = {
            'Nimhain': {
                'url': 'https://community.gemsofwar.com/u/Nimhain',
                'icon_url': 'https://sjc3.discourse-cdn.com/business5/'
                            'user_avatar/community.gemsofwar.com/nimhain/360/47049.png'},
            'Saltypatra': {
                'url': 'https://community.gemsofwar.com/u/saltypatra/',
                'icon_url': 'https://sjc3.discourse-cdn.com/business5/'
                            'user_avatar/community.gemsofwar.com/saltypatra/360/59750.png'},
        }
        e.set_author(name=author)
        details = author_details.get(author)
        if details:
            e.set_author(name=author, **details)

    def render_server_status(self, status):
        e = discord.Embed(title=_('[SERVER_STATUS]'), color=self.WHITE)
        e.timestamp = status['last_updated']
        e.set_footer(text='Last Updated')
        return self.render_embed(e, f'server_status.jinja', status=status['status'])

    def render_drop_chances(self, drop_chances, lang):
        chest = _('[CHEST]', lang)
        drop_rates = _('[DROP_RATES]')
        e = discord.Embed(title=f'{chest} {drop_rates}', color=self.WHITE)
        for chest_type, drops in drop_chances.items():
            field_lines = []
            for category, items in drops.items():
                if items:
                    field_lines.append(f'**__{category}__**')
                for item, chances in sorted(items.items(), key=lambda x: x[1]['chance'], reverse=True):
                    multiplier = chances.get('multiplier', '')
                    if multiplier:
                        multiplier = f' (x{multiplier})'
                    field_lines.append(f'{item}{multiplier}: {chances["chance"]}%')

            e.add_field(name=chest_type, value='\n'.join(field_lines))
        return e
