import asyncio
import datetime

from hashids import Hashids

from models import DB


class Toplist:
    def __init__(self):
        self.toplists = {}
        self.load()

    def load(self):
        db = DB()
        result = db.cursor.execute(f'SELECT * FROM Toplist;')
        toplists = result.fetchall()
        self.toplists = {
            t['id']: {
                'id': t['id'],
                'author_id': t['author_id'],
                'author_name': t['author_name'],
                'description': t['description'],
                'items': t['items'].split(','),
                'created': t['created'],
                'modified': t['modified'],
            }
            for t in toplists
        }
        db.close()

    def get(self, toplist_id):
        return self.toplists.get(toplist_id)

    async def add(self, author_id, author_name, description, items):
        hashids = Hashids(salt=author_name)
        new_id = hashids.encode(len(self.toplists)).lower()
        toplist = {
            'id': new_id,
            'author_id': author_id,
            'author_name': author_name,
            'description': description,
            'items': items.split(','),
            'created': datetime.datetime.now(),
            'modified': datetime.datetime.now(),
        }
        self.toplists[new_id] = toplist
        lock = asyncio.Lock()
        async with lock:
            db = DB()
            db.cursor.execute(
                'REPLACE INTO Toplist (id, author_id, author_name, description, items, created, modified) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (new_id,
                 author_id,
                 author_name,
                 description,
                 items,
                 toplist['created'],
                 toplist['modified'],
                 ))
            db.commit()
            db.close()
        return new_id

    def __len__(self):
        return len(self.toplists)

    def __iter__(self):
        yield from self.toplists.values()
