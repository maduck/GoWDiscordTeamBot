import discord
from jinja2 import Environment, FileSystemLoader

from configurations import CONFIG
from game_constants import RARITY_COLORS
from util import flatten


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

    def render_pet(self, pet, shortened):
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
        troop_list = ['{0} ({1})'.format(*troop) for troop in traitstone['troops']]
        troops = self.trim_text_to_length(", ".join(sorted(troop_list)), 900, ',', ', ...')
        class_list = ['{0} ({1})'.format(*_class) for _class in traitstone['classes']]
        classes = self.trim_text_to_length(", ".join(sorted(class_list)), 900, ',', ', ...')
        kingdom_list = [k for k in traitstone['kingdoms']]
        kingdoms = self.trim_text_to_length(", ".join(sorted(kingdom_list)), 900, ',', ', ...')
        return self.render_embed(e, 'traitstone.jinja',
                                 traitstone=traitstone, troops=troops, classes=classes, kingdoms=kingdoms)

    def render_talent(self, tree, shortened):
        e = discord.Embed(color=self.WHITE)
        if shortened:
            e.title = tree["name"]
            return self.render_embed(e, 'talent_shortened.jinja', tree=tree)

        e.title = 'Talent search found one exact match'
        return self.render_embed(e, 'talent.jinja', tree=tree)

    def render_team(self, team, author, shortened):
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
        input_text = break_character.join(lines) + break_character
        trimmed_text = cls.trim_text_to_length(input_text, limit)
        return trimmed_text.split(break_character)

    @classmethod
    def trim_news_to_length(cls, text, link, max_length=900):
        trimmed_text = cls.trim_text_to_length(text, max_length)
        read_more = ''
        if len(trimmed_text) != len(text):
            read_more = '[...] '
        result = f'{trimmed_text}{read_more}\n\n[Read full news article]({link}).'
        return result

    def render_events(self, events):
        e = discord.Embed(title='Upcoming GoW Events', color=self.WHITE)
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
        e.add_field(name='Spoilers', value='\n'.join(message_lines))
        return e
