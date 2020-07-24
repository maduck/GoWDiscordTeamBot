help_titles = {
    'en': 'Help',
    'fr': 'Aide',
    'de': 'Hilfe',
}
help_texts = {
    'en': {
        'Team Codes': '• __Basics__: Just post your team codes, e.g. `[1075,6251,6699,6007,3010,3,1,1,1,3,1,1,'
                      '14007]`. The bot will automatically answer with the troops posted in the code. The code '
                      'can be embedded within more text, and does not need to stand alone.\n\n'
                      '• __Language support__: All GoW languages are supported, put the two country code letters '
                      '(en, fr, de, ru, it, es, cn) in front of the team code, e.g. `cn[1075,6251,6699,6007,3010,'
                      '3,1,1,1,3,1,1,14007]`\n\n'
                      '• __Mini format__: Put a "-" in front of the code to make it appear in a small box, '
                      'e.g. `-[1075,6251,6699,6007]`, or with language `de-[1075,6251,6699,6007]`.',
        'Searches': '• __Basics__: the following searches are supported:\n'
                    ' - `{0}troop <search>`, e.g. `{0}troop elemaugrim`.\n'
                    ' - `{0}weapon <search>`, e.g. `{0}weapon mang`.\n'
                    ' - `{0}pet <search>`, e.g. `{0}pet puddling`.\n'
                    ' - `{0}class <search>`, e.g. `{0}class archer`.\n'
                    ' - `{0}talent <search>`, e.g. `{0}talent mana source`.\n'
                    ' - `{0}kingdom <search>`, e.g. `{0}kingdom karakoth`.\n'
                    '• __Rules__:\n'
                    '  - Search both works for ids and parts of their names.\n'
                    '  - Search is _not_ case sensitive.\n'
                    '  - Spaces, apostrophes (\') and dashes (-) will be ignored.\n\n'
                    '  - Multiple results will show a list of matched troops.\n'
                    'If one matching item is found, the side color will reflect the troop\'s base rarity.\n\n'
                    '• __Language support__: All GoW languages are supported, put the two country code letters '
                    '(en, fr, de, ru, it, es, cn) in front of the command, e.g. `de{0}troop '
                    'elemaugrim`. Localized searches will only look for troop names with their respective '
                    'translations.',
        'Other commands': '• __Prefix__: enter `{0}prefix <new_prefix>` to set a new prefix. Only the server owner '
                          'can do that.\n'
                          '__Short help__: enter `{0}quickhelp` to open a short overview of all commands.'
    },
}


def get_help_text(prefix, lang):
    help_title = help_titles.get(lang, help_titles['en'])
    help_content = help_texts.get(lang, help_texts['en'])
    return help_title, {section: text.format(prefix) for section, text in help_content.items()}
