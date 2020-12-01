CREATE TABLE IF NOT EXISTS Language
(
    guild_id INTEGER constraint Language_pk PRIMARY KEY,
    value    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Prefix
(
    guild_id INTEGER constraint Prefix_pk PRIMARY KEY,
    value    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Subscription
(
    channel_id INTEGER constraint Subscription_pk PRIMARY KEY,
    guild_id   INTEGER,
    guild      TEXT,
    channel    TEXT,
    pc         BOOLEAN,
    switch     BOOLEAN
);

CREATE TABLE IF NOT EXISTS Toplist
(
	id          TEXT NOT NULL constraint Toplist_pk PRIMARY KEY,
	author_id   TEXT NOT NULL,
	author_name TEXT NOT NULL,
	description TEXT NOT NULL,
	items       TEXT NOT NULL,
    created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

