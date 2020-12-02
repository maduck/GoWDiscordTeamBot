import asyncio
import datetime

from hashids import Hashids

from models import DB

MAX_TOPLISTS = 5


class ToplistError(Exception):
    pass


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

    async def add(self, author_id, author_name, description, items, update_id):
        _id = update_id
        if not update_id:
            if len(self.get_my_toplists(author_id)) >= MAX_TOPLISTS:
                raise ToplistError(f'You have reached the maximum amount of {MAX_TOPLISTS} toplists.'
                                   f' Please consider deleting some using `!toplist delete <id>`.')
            _id = self.generate_new_id(author_name)
        elif update_id not in self.toplists:
            raise ToplistError('The toplist you are trying to update does not exist.')
        elif str(author_id) != self.toplists[update_id]['author_id']:
            raise ToplistError('The toplist you are trying to update belongs to someone else.')

        chopped_items = [i.strip() for i in items.split(',')][:30]
        toplist = {
            'id': _id,
            'author_id': str(author_id),
            'author_name': author_name,
            'description': description,
            'items': chopped_items,
            'created': datetime.datetime.utcnow(),
            'modified': datetime.datetime.utcnow(),
        }
        self.toplists[_id] = toplist
        lock = asyncio.Lock()
        async with lock:
            db = DB()
            db.cursor.execute(
                'REPLACE INTO Toplist (id, author_id, author_name, description, items, modified) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (_id,
                 author_id,
                 author_name,
                 description,
                 ','.join(chopped_items),
                 toplist['modified'],
                 ))
            db.commit()
            db.close()
        return _id

    async def remove(self, author_id, _id):
        if _id not in self.toplists:
            raise ToplistError('The toplist you are trying to delete does not exist.')
        elif str(author_id) != self.toplists[_id]['author_id']:
            raise ToplistError('The toplist you are trying to delete belongs to someone else.')
        lock = asyncio.Lock()
        async with lock:
            db = DB()
            db.cursor.execute('DELETE FROM Toplist WHERE id = ?', (_id,))
            db.commit()
            db.close()
        del (self.toplists[_id])

    def get_my_toplists(self, author_id):
        return [t for t in self.toplists.values() if str(author_id) == t['author_id']]

    def __len__(self):
        return len(self.toplists)

    def __iter__(self):
        yield from self.toplists.values()

    def generate_new_id(self, author_name):
        hashids = Hashids(salt=author_name)
        offset = 0
        while True:
            _id = hashids.encode(len(self.toplists) + offset).lower()
            if _id not in self.toplists:
                return _id
            offset += 1
