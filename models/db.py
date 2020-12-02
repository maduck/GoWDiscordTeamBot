import sqlite3

from configurations import CONFIG


class DB:
    def __init__(self):
        self.filename = CONFIG.get('database')
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        self.conn = sqlite3.connect(self.filename, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
