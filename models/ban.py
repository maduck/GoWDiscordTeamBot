import datetime

from models import DB


class Ban:
    @staticmethod
    def get(guild_id):
        db = DB()
        result = db.cursor.execute(f'SELECT * FROM Ban WHERE guild_id = ?;', (guild_id,))
        ban = result.fetchone()
        db.close()
        return ban

    @staticmethod
    def add(guild_id, reason, author_name):
        db = DB()
        db.cursor.execute(
            'REPLACE INTO Ban (guild_id, reason, author_name, ban_time)'
            'VALUES (?, ?, ?, ?)',
            (guild_id,
             reason,
             author_name,
             datetime.datetime.utcnow(),
             ))
        db.commit()
        db.close()
