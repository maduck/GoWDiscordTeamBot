#!/usr/bin/env python3
import logging
import os
import re

import discord

from team_expando import TeamExpander

TOKEN = os.getenv('DISCORD_TOKEN')
LOGLEVEL = logging.DEBUG

formatter = logging.Formatter('%(asctime)-15s [%(levelname)s] %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(LOGLEVEL)
log = logging.getLogger(__name__)

log.setLevel(logging.DEBUG)
log.addHandler(handler)


async def pluralize_author(author):
    if author[-1] == 's':
        author += "'"
    else:
        author += "'s"
    return author


class DiscordBot(discord.Client):
    BOT_NAME = 'Garys GoW Team Bot'
    BASE_GUILD = 'GoW Bot Dev'
    VERSION = '0.1'
    SEARCH_COMMANDS = (
        {'key': 'troop',
         'search': re.compile(r'^(?P<lang>en|fr|de|ru|it|es|cn)?!troop (?P<search>.*)$')},
    )

    def __init__(self, *args, **kwargs):
        log.debug(f'--------------------------- Starting {self.BOT_NAME} v{self.VERSION} --------------------------')
        super().__init__(*args, **kwargs)
        self.permissions = self.generate_permissions()
        self.invite_url = 'https://discordapp.com/api/oauth2/authorize?client_id={{}}&scope=bot&permissions={}'
        self.invite_url = self.invite_url.format(self.permissions.value)
        self.my_emojis = {}
        self.expander = TeamExpander()

    @staticmethod
    def generate_permissions():
        permissions = discord.Permissions.none()
        needed_permissions = [
            'add_reactions',
            'read_messages',
            'send_messages',
            'manage_messages',
            'read_message_history',
            'external_emojis',
        ]
        for perm_name in needed_permissions:
            setattr(permissions, perm_name, True)
        log.debug(f'Permissions required: {", ".join([p for p, v in permissions if v])}')
        return permissions

    async def on_ready(self):
        self.invite_url = self.invite_url.format(self.user.id)
        log.debug(f'Logged in as {self.user.name}')
        log.info(f'Invite with: {self.invite_url}')
        log.debug(f'Active in {", ".join([g.name for g in self.guilds])}')
        await self.update_base_emojis()

    async def update_base_emojis(self):
        for guild in self.guilds:
            if guild.name == self.BASE_GUILD:
                for emoji in guild.emojis:
                    self.my_emojis[emoji.name] = str(emoji)

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        for command in self.SEARCH_COMMANDS:
            match = command['search'].match(message.content)
            if match:
                function_name = f'handle_{command["key"]}_search'
                search_function = getattr(self, function_name)
                groups = match.groupdict()
                search_term = groups['search']
                lang = groups['lang']
                await search_function(message, search_term, lang)
                return
        if "[" in message.content:
            await self.handle_team_code(message)

    async def handle_troop_search(self, message, search_term, lang):
        result = self.expander.search_troop(search_term, lang)
        e = discord.Embed(title='Troop search')
        if result:
            mana = self.my_emojis.get(result['color_code'])
            message_lines = [
                result["description"],
                '',
                f'**{result["spell_title"]}** {result["spell"]["name"]}: {result["spell"]["description"]}',
                f'**{result["rarity_title"]}** {result["rarity"]}',
                f'**{result["roles_title"]}** {", ".join(result["roles"])}',
                f'**Type** {result["type"]}',
            ]
            e.add_field(name=f'{mana} {result["name"]}', value='\n'.join(message_lines))
            trait_list = [f'**{trait["name"]}** - {trait["description"]}' for trait in result['traits']]
            traits = '\n'.join(trait_list)
            e.add_field(name=result["traits_title"], value=traits, inline=False)
        else:
            e.add_field(name=search_term, value='did not yield any result')
        await message.channel.send(embed=e)

    async def handle_team_code(self, message):
        team = self.expander.get_team_from_message(message.content)
        if not team:
            log.debug(f'nothing found in message {message.content}')
            return
        log.debug(f'[{message.guild}][{message.channel}] sending result to {message.author.display_name}: {team}')
        color = discord.Color.from_rgb(19, 227, 246)
        author = message.author.display_name
        author = await pluralize_author(author)
        e = discord.Embed(title=f"{author} team", color=color)
        troops = [f'{self.my_emojis.get(t[0], f":{t[0]}:")} {t[1]}' for t in team['troops']]
        team_text = '\n'.join(troops)
        e.add_field(name=team['troops_title'], value=team_text, inline=True)
        if team['banner']:
            banner_texts = [f'{self.my_emojis.get(d[0], f":{d[0]}:")} {abs(d[1]) * f"{d[1]:+d}"[0]}' for d in
                            team['banner']['description']]
            e.add_field(name=team['banner']['name'], value='\n'.join(banner_texts), inline=True)
        if team['class']:
            e.add_field(name=f'{team["class_title"]}: {team["class"]}', value='\n'.join(team['talents']),
                        inline=False)
        await message.channel.send(embed=e)


if __name__ == '__main__':
    client = DiscordBot()
    client.run(TOKEN)
