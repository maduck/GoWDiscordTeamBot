tower_help_titles = {
    'en': 'Tower of Doom Help',
}
tower_help_texts = {
    'en': {
        'Basics': 'Users can use the `{0}tower` command to enter Scroll data for the Tower of Doom, '
                  'then display it for easy viewing. Each Tower is specific to the channel it is in.',
        'Entering Data': 'To enter data, use the `{0}tower` command. Shortened names or aliases can be used.\n'
                         '`{0}tower 4 ii unlock`\n'
                         '`{0}tower 5 rare fi`\n'
                         'You can set a whole floor in one line:\n'
                         '`{0}tower 6 armor fireball unlock haste`\n',
        'Displaying Data': 'To display the data, simply use the `{0}tower` command with no arguments.',
        'Clearing Data': 'To clear the tower data, simply use the `{0}towerclear` command with no arguments.',
        'Configuration': 'To configure the tower utility, use `{0}towerconfig`.\n'
                         '`{0}towerconfig short true` for short responses to edits.\n'
                         '`{0}towerconfig rooms III iii,rare,green` to set the room aliases. '
                         'Comma separated values.\n'
                         '`{0}towerconfig scrolls armor :shield:,Armor` to set scroll aliases. '
                         'First value will be used for display.\n',

    }
}


def get_help_texts(prefix, lang, titles, texts):
    translated_title = titles.get(lang, titles['en'])
    translated_text = texts.get(lang, texts['en'])
    return translated_title, {section: text.format(prefix) for section, text in translated_text.items()}


def get_tower_help_text(prefix, lang):
    return get_help_texts(prefix, lang, tower_help_titles, tower_help_texts)
