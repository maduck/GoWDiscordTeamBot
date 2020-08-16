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
                embed.add_field(
                    name=splitted[:title_end],
                    value=splitted[title_end+4:],
                    inline=True)
        return embed

    def render_weapon(self, weapon, shortened):
        rarity_color = RARITY_COLORS.get(weapon['raw_rarity'], RARITY_COLORS['Mythic'])
        color = discord.Color.from_rgb(*rarity_color)
        e = discord.Embed(title='Weapon search', color=color)
        if shortened:
            return self.render_embed(e, 'weapon_shortened.jinja', weapon=weapon)

        thumbnail_url = f'{CONFIG.get("graphics_url")}/Spells/Cards_{weapon["spell_id"]}_thumb.png'
        e.set_thumbnail(url=thumbnail_url)
        if 'release_date' in weapon:
            e.set_footer(text='Release date')
            e.timestamp = weapon["release_date"]
        return self.render_embed(e, 'weapon.jinja', weapon=weapon)

    def render_pet(self, pet, shortened):
        e = discord.Embed(title='Pet search', color=self.WHITE)
        if shortened:
            return self.render_embed(e, 'pet_shortened.jinja', pet=pet)

        thumbnail_url = f'{CONFIG.get("graphics_url")}/Pets/Cards_{pet["filename"]}_thumb.png'
        e.set_thumbnail(url=thumbnail_url)
        if 'release_date' in pet:
            e.set_footer(text='Release date')
            e.timestamp = pet["release_date"]
        return self.render_embed(e, 'pet.jinja', pet=pet)

    def render_troop(self, troop, shortened):
        rarity_color = RARITY_COLORS.get(troop['raw_rarity'], RARITY_COLORS['Mythic'])
        if 'Boss' in troop['raw_types']:
            rarity_color = RARITY_COLORS['Doomed']
        e = discord.Embed(title='Troop search', color=discord.Color.from_rgb(*rarity_color))
        if shortened:
            return self.render_embed(e, 'troop_shortened.jinja', troop=troop)

        thumbnail_url = f'{CONFIG.get("graphics_url")}/Troops/Cards_{troop["filename"]}_thumb.png'
        e.set_thumbnail(url=thumbnail_url)

        if 'release_date' in troop:
            e.set_footer(text='Release date')
            e.timestamp = troop["release_date"]
        return self.render_embed(e, 'troop.jinja', troop=troop)

    def render_talent_tree(self, tree, shortened):
        e = discord.Embed(color=self.WHITE)
        if shortened:
            e.title = tree["name"]
            return self.render_embed(e, 'talent_shortened.jinja', tree=tree)

        e.title = 'Talent search'
        return self.render_embed(e, 'talent.jinja', tree=tree)

    def render_team(self, team, author, shortened):
        color = discord.Color.from_rgb(*RARITY_COLORS['Mythic'])
        e = discord.Embed(color=color)
        if shortened:
            troops = [f'{t[1]}' for t in team['troops']]
            e.title = ', '.join(troops)
            return self.render_embed(e, 'team_shortened.jinja', team=team)

        if team['banner']:
            thumbnail_url = f'{CONFIG.get("graphics_url")}/Banners/Banners_{team["banner"]["filename"]}_thumb.png'
            e.set_thumbnail(url=thumbnail_url)

        e.title=f"{author} team"
        return self.render_embed(e, 'team.jinja', team=team)

    def render_kingdom(self, kingdom, shortened):
        e = discord.Embed(title='Kingdom search', color=self.WHITE)
        underworld = 'underworld' if kingdom['underworld'] else ''
        thumbnail_url = f'{CONFIG.get("graphics_url")}/Maplocations{underworld}_{kingdom["filename"]}_thumb.png'
        e.set_thumbnail(url=thumbnail_url)

        if shortened:
            return self.render_embed(e, 'kingdom_shortened.jinja', kingdom=kingdom)
        return self.render_embed(e, 'kingdom.jinja', kingdom=kingdom)

    def render_class(self, _class, shortened):
        e = discord.Embed(title='Class search', color=self.WHITE)
        if shortened:
            return self.render_embed(e, 'class_shortened.jinja', _class=_class)

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
