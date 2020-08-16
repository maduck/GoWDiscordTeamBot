import discord

from configurations import CONFIG
from game_constants import RARITY_COLORS
from util import flatten
from jinja2 import Environment, FileSystemLoader


class Views:
    WHITE = discord.Color.from_rgb(254, 254, 254)
    BLACK = discord.Color.from_rgb(0, 0, 0)
    RED = discord.Color.from_rgb(255, 0, 0)

    def __init__(self, emojis):
        self.my_emojis = emojis
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))

    def render_embed(self, embed, template_name, **kwargs):
        self.jinja_env.filters['emoji'] = self.my_emojis.get
        self.jinja_env.globals.update({
            'emoji': self.my_emojis.get,
        })

        template = self.jinja_env.get_template(template_name)
        content = template.render(**kwargs)

        for i, splitted in enumerate(content.split('<T>')):
            if i == 0:
                embed.description = splitted
            else:
                title_end = splitted.index('</T>')
                embed.add_field(
                    name=splitted[:title_end],
                    value=splitted[title_end+4:],
                    inline=True)
        return embed

    def render_weapon(self, weapon, shortened=False):
        rarity_color = RARITY_COLORS.get(weapon['raw_rarity'], RARITY_COLORS['Mythic'])
        color = discord.Color.from_rgb(*rarity_color)
        e = discord.Embed(title='Weapon search', color=color)
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Spells/Cards_{weapon["spell_id"]}_thumb.png'
        e.set_thumbnail(url=thumbnail_url)

        if 'release_date' in weapon:
            e.set_footer(text='Release date')
            e.timestamp = weapon["release_date"]

        return self.render_embed(e, 'weapon.jinja', weapon=weapon)

    def render_pet(self, pet, shortened):
        e = discord.Embed(title='Pet search', color=self.WHITE)
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Pets/Cards_{pet["filename"]}_thumb.png'
        e.set_thumbnail(url=thumbnail_url)
        mana = self.my_emojis.get(pet['color_code'])
        effect_data = ''
        if pet['effect_data']:
            effect_data = f' ({pet["effect_data"]})'
        message_lines = [
            f'**{pet["effect_title"]}**: {pet["effect"]}{effect_data}',
            f'**{pet["kingdom_title"]}**: {pet["kingdom"]}',
        ]
        if 'release_date' in pet:
            e.set_footer(text='Release date')
            e.timestamp = pet["release_date"]
        e.add_field(name=f'{mana} {pet["name"]} `#{pet["id"]}`', value='\n'.join(message_lines))
        return e

    def render_troop(self, troop, shortened):
        rarity_color = RARITY_COLORS.get(troop['raw_rarity'], RARITY_COLORS['Mythic'])
        if 'Boss' in troop['raw_types']:
            rarity_color = RARITY_COLORS['Doomed']
        color = discord.Color.from_rgb(*rarity_color)
        mana = self.my_emojis.get(troop['color_code'])
        mana_display = f'{troop["spell"]["cost"]}{mana} '
        e = discord.Embed(title='Troop search', color=color)
        if shortened:
            e.description = f'**{mana_display}{troop["name"]}**'
            attributes = flatten(troop["type"], troop["roles"], troop["rarity"], troop["kingdom"])
            e.description += f' ({", ".join(attributes)}) | {troop["spell"]["description"]}'

            trait_list = [f'{trait["name"]}' for trait in troop['traits']]
            e.description += f'\n{", ".join(trait_list)}'
        else:
            thumbnail_url = f'{CONFIG.get("graphics_url")}/Troops/Cards_{troop["filename"]}_thumb.png'
            e.set_thumbnail(url=thumbnail_url)
            message_lines = [
                f'**{troop["spell"]["name"]}**: {troop["spell"]["description"]}',
                '',
                f'**{troop["kingdom_title"]}**: {troop["kingdom"]}',
                f'**{troop["rarity_title"]}**: {troop["rarity"]}',
                f'**{troop["roles_title"]}**: {", ".join(troop["roles"])}',
                f'**{troop["type_title"]}**: {troop["type"]}',
            ]

            description = ''
            if troop['description']:
                description = f' **{troop["description"]}**'

            e.description = f'**{mana_display}{troop["name"]}** `#{troop["id"]}`{description}'
            e.description += '\n' + '\n'.join(message_lines)

            trait_list = [f'**{trait["name"]}**: {trait["description"]}' for trait in troop['traits']]
            if 'release_date' in troop:
                e.set_footer(text='Release date')
                e.timestamp = troop["release_date"]
            traits = '\n'.join(trait_list)
            e.add_field(name=troop["traits_title"], value=traits, inline=False)
        return e

    def render_talent_tree(self, tree, shortened):
        e = discord.Embed(title='Talent search', color=self.WHITE)
        talents = [f'**{t["name"]}**: ({t["description"]})' for t in tree['talents']]
        e.add_field(name=f'__{tree["name"]}__', value='\n'.join(talents), inline=True)
        classes = [f'{c["name"]} `#{c["id"]}`' for c in tree['classes']]
        e.add_field(name='__Classes using this Talent Tree:__', value=', '.join(classes), inline=False)
        return e

    def banner_colors(self, banner):
        return [f'{self.my_emojis.get(d[0], f":{d[0]}:")}{abs(d[1]) * f"{d[1]:+d}"[0]}' for d in banner['colors']]

    def format_output_team(self, team, color, author):
        e = discord.Embed(title=f"{author} team", color=color)
        troops = [f'{self.my_emojis.get(t[0], f":{t[0]}:")} {t[1]}' for t in team['troops']]
        team_text = '\n'.join(troops)
        e.add_field(name=team['troops_title'], value=team_text, inline=True)
        if team['banner']:
            banner_url = f'{CONFIG.get("graphics_url")}/Banners/Banners_{team["banner"]["filename"]}_thumb.png'
            e.set_thumbnail(url=banner_url)
            banner_colors = self.banner_colors(team['banner'])
            e.add_field(name=team['banner']['name'], value='\n'.join(banner_colors), inline=True)
        if team['class']:
            talents = '\n'.join(team['talents'])
            if all([t == '-' for t in team['talents']]):
                talents = '-'
            e.add_field(name=f'{team["class_title"]}: {team["class"]}', value=talents,
                        inline=False)
        return e

    def format_output_team_shortened(self, team, color):
        e = discord.Embed(color=color)
        troops = [f'{t[1]}' for t in team['troops']]
        e.title = ', '.join(troops)
        descriptions = []

        if team['banner']:
            banner_texts = [f'{self.my_emojis.get(d[0], f":{d[0]}:")}{abs(d[1]) * f"{d[1]:+d}"[0]}' for d in
                            team['banner']['colors']]
            banner = '{banner_name} {banner_texts}'.format(
                banner_name=team['banner']['name'],
                banner_texts=' '.join(banner_texts)
            )
            descriptions.append(banner)
        if team['class']:
            descriptions.append(team["class"])
        if team['talents'] and not all([i == '-' for i in team['talents']]):
            descriptions.append(', '.join(team['talents']))
        e.description = '\n'.join(descriptions)
        return e

    def render_kingdom(self, kingdom, shortened=False):
        e = discord.Embed(title='Kingdom search', color=self.WHITE)
        underworld = 'underworld' if kingdom['underworld'] else ''
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Maplocations{underworld}_{kingdom["filename"]}_thumb.png'
        e.set_thumbnail(url=thumbnail_url)
        kingdom_troops = ', '.join([f'{troop["name"]} `{troop["id"]}`' for troop in kingdom['troops']])
        colors = [f'{self.my_emojis.get(c, f":{c}:")}' for c in kingdom['colors']]
        banner_colors = self.banner_colors(kingdom['banner'])
        message_lines = []
        if not shortened:
            message_lines.append(kingdom['punchline'])
            message_lines.append(kingdom['description'])

        message_lines.append(f'**{kingdom["banner_title"]}**: {kingdom["banner"]["name"]} {" ".join(banner_colors)}')

        if 'primary_color' in kingdom and 'primary_stat' in kingdom:
            primary_mana = self.my_emojis.get(kingdom['primary_color'])
            deed_emoji = self.my_emojis.get(f'deed_{kingdom["primary_color"]}')
            message_lines.extend([
                f'**{kingdom["color_title"]}**: {primary_mana} / {deed_emoji} {kingdom["deed"]}',
                f'**{kingdom["stat_title"]}**: {kingdom["primary_stat"]}',
            ])
        message_lines.append(f'\n**{kingdom["linked_map"]}**: {kingdom["linked_kingdom"]}'
                             if kingdom['linked_kingdom'] else '')
        if not shortened:
            message_lines.append(f'**{kingdom["troop_title"]}**: {kingdom_troops}')
        e.add_field(name=f'{kingdom["name"]} `#{kingdom["id"]}` {"".join(colors)} ({kingdom["map"]})',
                    value='\n'.join(message_lines))
        return e

    def render_class(self, _class, shortened):
        e = discord.Embed(title='Class search', color=self.WHITE)
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Classes_{_class["code"]}_thumb.png'
        e.set_thumbnail(url=thumbnail_url)
        return self.render_embed(e, 'class.jinja', _class=_class)

    @staticmethod
    def trim_text_lines_to_length(lines, limit):
        breakdown = [sum([len(c) + 2 for c in lines[0:i]]) < limit for i in range(len(lines))]
        if all(breakdown):
            return lines
        return lines[:breakdown.index(False) - 1]

    @staticmethod
    def trim_news_to_length(text, link, max_length=900):
        break_character = '\n'
        input_text = f'{text}{break_character}'
        trimmed_text = input_text[:input_text[:max_length].rfind(break_character)]
        read_more = ''
        if len(trimmed_text + break_character) != len(input_text):
            read_more = '[...] '
        result = f'{trimmed_text}{read_more}\n\n[Read full news article]({link}).'
        return result

    def render_events(self, events):
        e = discord.Embed(title='Spoilers', color=self.WHITE)
        message_lines = ['```']
        last_event_date = events[0]['start']
        for event in events:
            if event['start'] > last_event_date and event['start'].weekday() == 0:
                message_lines.append('')
            last_event_date = event['start']
            message_lines.append(f'{event["start"].strftime("%b %d")} - '
                                 f'{event["end"].strftime("%b %d")} '
                                 f'{event["type"]}'
                                 f'{":" if event["extra_info"] else ""} '
                                 f'{event["extra_info"]}')
        message_lines = self.trim_text_lines_to_length(message_lines, 900)
        message_lines.append('```')
        e.add_field(name='Upcoming Events', value='\n'.join(message_lines))
        return e
