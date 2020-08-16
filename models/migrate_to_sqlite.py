import json

from models.db import DB

db = DB()
db.cursor.execute('CREATE TABLE Prefix (guild_id INTEGER UNIQUE, value TEXT NOT NULL);')

with open('prefixes.json') as f:
    prefixes = json.load(f)
for guild_id, prefix in prefixes.items():
    db.cursor.execute('INSERT INTO Prefix VALUES (?, ?);', (guild_id, prefix))

db.cursor.execute('CREATE TABLE Language (guild_id INTEGER UNIQUE, value TEXT NOT NULL);')
with open('languages.json') as f:
    languages = json.load(f)
for guild_id, lang in languages.items():
    db.cursor.execute('INSERT INTO Language VALUES (?, ?);', (guild_id, lang))

db.cursor.execute('CREATE TABLE Subscription '
                  '(channel_id INTEGER UNIQUE, guild_id INTEGER, guild TEXT, channel TEXT, pc BOOLEAN, switch BOOLEAN);')
with open('subscriptions.json') as f:
    subscriptions = json.load(f)
for subscription_id, s in subscriptions.items():
    db.cursor.execute('INSERT INTO Subscription VALUES (?, ?, ?, ?, ?, ?);',
                      (s['channel_id'], s['channel_name'], s['guild_id'], s['guild_name'],
                       s.get('pc', False), s.get('switch', False))
                      )

db.commit()
