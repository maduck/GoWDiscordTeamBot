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
    'fr': {
        'Codes d\'équipe': '• __Les bases__: Postez simplement votre code d\'équipe, par exemple: [1075,6251,6699,'
                           '6007,3010,3,1,1,1,3,1,1,14007]. Le bot répondra automatiquement en affichant les troupes '
                           'postées dans le code. Ce code peut être intégré dans du texte supplémentaire et il ne '
                           'nécessite pas d\'être seul sur une ligne.\n\n '
                           '• __Support linguistique__: Toutes les langues utilisées dans GoW sont supportées. '
                           'Préfixez simplement votre code avec les deux lettres de votre code pays (en, fr, de, ru, '
                           'it, es, cn),par exemple: fr[1075,6251,6699,6007,3010,3,1,1,1,3,1,1,14007]\n\n '
                           '• __Format raccourci__: Utilisez le caractère "-" (tiret) en début de code pour que le '
                           'résultat apparaisse en mode minimal et condensé, par exemple -[1075,6251,6699,6007], '
                           'ou avec le code langue fr-[1075,6251,6699,6007].',
        'Recherches': '• __Les bases__: les recherches suivantes sont supportées:\n'
                      ' - `{0}troop <recherche>`, par exemple `fr{0}troop élémaugrim`.\n'
                      ' - `{0}weapon <recherche>`\n'
                      ' - `{0}pet <recherche>`\n'
                      ' - `{0}class <recherche>`\n'
                      ' - `{0}kingdom <recherche>`\n'
                      ' - `{0}talent <recherche>`\n'
                      '• __Règles__:\n'
                      '  - La recherche fonctionne avec les numéros ids et les parties de noms.\n'
                      '  - La recherche n\'est sensible ni aux majuscules ni aux minuscules.\n'
                      '  - Les espaces, les apostrophes (\') et les tirets (-) peuvent être ignorés.\n\n'
                      '  - Plusieurs résultats peuvent être affichés, en tant que troupes, s\'ils correspondent '
                      'à la recherche.\n '
                      'Si une seule troupe correspond à la recherche effectuée, la couleur du bord du résultat '
                      'montrera la rareté de base de la troupe.\n\n '
                      '• __Support linguistique__: Toutes les langues utilisées dans GoW sont supportées. Préfixez '
                      'simplement votre code avec les deux lettres de votre code pays (en, fr, de, ru, it, es, '
                      'cn). Les recherches dans la langue correspondante s\'effectueront uniquement sur les noms '
                      'de troupes dans la langue choisie.',
        'Préfixe': '• __Les Bases__: tapez `{0}prefix <nouveau_préfixe>` pour configurer un nouveau '
                   'préfixe. Seul le propriétaire du serveur peut faire ce changement.',
        'Aide rapide': '• __Les Bases__: tapez `{0}quickhelp` pour ouvrir un court aperçu de toutes les commandes.\n'
    },
}


def get_help_text(prefix, lang):
    help_title = help_titles.get(lang, help_titles['en'])
    help_content = help_texts.get(lang, help_texts['en'])
    return help_title, {section: text.format(prefix) for section, text in help_content.items()}
