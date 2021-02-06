# Discord bot for handling Gems of War team codes

[![Maintainability](https://api.codeclimate.com/v1/badges/b4b04e1e077f2edc8b6e/maintainability)](https://codeclimate.com/github/maduck/GoWDiscordTeamBot/maintainability) [![Discord Bots](https://top.gg/api/widget/status/733399051797790810.svg)](https://top.gg/bot/733399051797790810) [![Discord Bots](https://top.gg/api/widget/servers/733399051797790810.svg)](https://top.gg/bot/733399051797790810)

![bot screenshot](https://garyatrics.com/images/bot_weapon_search.png)

you're on your own installing and using this.
Keep in mind I will not be providing the needed game files (World.json and translations).

## contributions
see [CONTRIBUTIONS](CONTRIBUTING.md)

## copying
see [LICENSE](LICENSE.md)

## install
* install python 3.8+
* create a virtualenv "venv"
* install all packages from requirements.txt

## configure

* copy file `settings_default.json` into `settings.json`. Adapt settings there.
* create folder `game_assets` (or whatever you configured as `game_assets_folder`)
* place the following files into that folder:
  - Unencrypted `World.json`
  - Unencrypted language translation json files
  - Optional: `Soulforge.json` for `!soulforge` command
  - Optional: `User.json` for `!events`, `!spoilers` and some more
  - Optional: `Campaign.json` for `!campaign` command

## run
* export the ENV DISCORD_TOKEN (register the app on discord to get a token)
* run bot.py
