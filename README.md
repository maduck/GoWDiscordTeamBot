# Discord bot for handling Gems of War team codes

[![Maintainability](https://api.codeclimate.com/v1/badges/b4b04e1e077f2edc8b6e/maintainability)](https://codeclimate.com/github/maduck/GoWDiscordTeamBot/maintainability)

![bot screenshot](https://garyatrics.com/images/bot_weapon_search.png)

Do you want to just use the bot? [Invite Link](https://discord.com/discovery/applications/733399051797790810).
If you are here for the source code, keep on reading.

## disclaimer

This bot needs to have some game files to be run properly. Those game files are proprietary to 505 Games, and are
encrypted. If you don't know how to receive the data, you can stop reading here. Due to copyright, I will not be
providing any of those files.

## contributions
see [CONTRIBUTIONS](CONTRIBUTING.md)

## copying
see [LICENSE](LICENSE.md)

## install

* install python 3.12+
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

* export the environment variable `DISCORD_TOKEN` (register the app on discord to get a token)
* run bot.py
