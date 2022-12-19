import asyncio
import datetime

from hashids import Hashids

from models import DB

MAX_TOPLIST_LENGTH = 30
MAX_TOPLISTS = 50


class ToplistError(Exception):
    pass


class Toplist:
    def __init__(self):
        self.toplists = {}
        self.load()

    def load(self):
        database = DB()
        result = database.cursor.execute('SELECT * FROM Toplist;')
        toplists = result.fetchall()
        self.toplists = {
            t['id']: {
                'id': t['id'],
                'author_id': t['author_id'],
                'author_name': t['author_name'],
                'description': t['description'],
                'items': t['items'].split(','),
                'created': t['created'].replace(tzinfo=datetime.timezone.utc),
                'modified': t['modified'].replace(tzinfo=datetime.timezone.utc),
            }
            for t in toplists
        }
        database.close()

    def get(self, toplist_id):
        return self.toplists.get(toplist_id)

    async def add(self, author_id, author_name, description, items, update_id):
        if not update_id:
            if len(self.get_my_toplists(author_id)) >= MAX_TOPLISTS:
                raise ToplistError(f'You have reached the maximum amount of '
                                   f'{MAX_TOPLISTS} toplists.'
                                   f' Please consider deleting some using '
                                   f'`!toplist delete <id>`.')
            update_id = self.generate_new_id(author_name)
        elif update_id not in self.toplists:
            raise ToplistError('The toplist you are trying to update does not exist.')
        elif str(author_id) != self.toplists[update_id]['author_id']:
            raise ToplistError('The toplist you are trying to update belongs to someone else.')

        chopped_items = [i.strip() for i in items.split(',')][:MAX_TOPLIST_LENGTH]
        toplist = {
            'id': update_id,
            'author_id': str(author_id),
            'author_name': author_name,
            'description': description,
            'items': chopped_items,
            'created': datetime.datetime.now(datetime.timezone.utc),
            'modified': datetime.datetime.now(datetime.timezone.utc),
        }
        lock = asyncio.Lock()
        async with lock:
            self.toplists[update_id] = toplist
            database = DB()
            database.cursor.execute(
                'REPLACE INTO Toplist (id, author_id, author_name, description, items, modified) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (update_id,
                 author_id,
                 author_name,
                 description,
                 ','.join(chopped_items),
                 toplist['modified'],
                 ))
            database.commit()
            database.close()
        return update_id

    async def remove(self, author_id, _id):
        if _id not in self.toplists:
            raise ToplistError('The toplist you are trying to delete does not exist.')
        if str(author_id) != self.toplists[_id]['author_id']:
            raise ToplistError('The toplist you are trying to delete belongs to someone else.')
        lock = asyncio.Lock()
        async with lock:
            database = DB()
            database.cursor.execute('DELETE FROM Toplist WHERE id = ?', (_id,))
            database.commit()
            database.close()
            del self.toplists[_id]

    async def append(self, _id, author_id, author_name, new_items):
        if _id not in self.toplists:
            raise ToplistError('The toplist you are trying to modify does not exist.')

        toplist = self.toplists[_id]
        old_items = ','.join(toplist['items'])
        items = ','.join([old_items, new_items])
        await self.add(author_id, author_name, toplist['description'], items, _id)
        return _id

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
