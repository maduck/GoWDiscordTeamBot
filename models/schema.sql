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
    id          TEXT NOT NULL
        constraint Toplist_pk PRIMARY KEY,
    author_id   TEXT NOT NULL,
    author_name TEXT NOT NULL,
    description TEXT NOT NULL,
    items       TEXT NOT NULL,
    created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS PetRescue
(
    id               INTEGER
        constraint PetRescue_pk primary key autoincrement,
    guild_name       text,
    guild_id         INTEGER,
    channel_name     text,
    channel_id       INTEGER,
    message_id       INTEGER,
    pet_id           INTEGER,
    alert_message_id INTEGER,
    pet_message_id   INTEGER,
    start_time       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lang             TEXT [2],
    mention          TEXT
);

CREATE TABLE IF NOT EXISTS PetRescueConfig
(
    guild_name     TEXT,
    guild_id       INTEGER,
    channel_name   TEXT,
    channel_id     INTEGER,
    mention        TEXT,
    delete_message INTEGER,
    delete_mention INTEGER,
    delete_pet     INTEGER
);

CREATE
    UNIQUE INDEX PetRescueConfig_index
    ON PetRescueConfig (guild_id, channel_id);

CREATE TABLE IF NOT EXISTS PetRescueStats
(
    pet_id  INTEGER,
    rescues INTEGER
);

CREATE TABLE IF NOT EXISTS Bookmark
(
    id          TEXT NOT NULL
        CONSTRAINT Bookmark_pk PRIMARY KEY,
    author_id   TEXT NOT NULL,
    author_name TEXT NOT NULL,
    description TEXT NOT NULL,
    team_code   TEXT NOT NULL,
    created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS Ban
(
    guild_id    INTEGER NOT NULL
        CONSTRAINT Ban_pk PRIMARY KEY,
    author_name TEXT    NOT NULL,
    reason      TEXT,
    ban_time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE
UNIQUE INDEX Ban_guild_id_uindex
    ON Ban (guild_id);

