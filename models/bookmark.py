import asyncio
import datetime

from hashids import Hashids

from models import DB

MAX_BOOKMARKS = 10


class BookmarkError(Exception):
    pass


class Bookmark:
    def __init__(self):
        self.bookmarks = {}
        self.load()

    def load(self):
        db = DB()
        result = db.cursor.execute(f'SELECT * FROM Bookmark;')
        bookmarks = result.fetchall()
        self.bookmarks = {
            b['id']: {
                'id': b['id'],
                'author_id': b['author_id'],
                'author_name': b['author_name'],
                'description': b['description'],
                'team_code': b['team_code'],
                'created': b['created'],
            }
            for b in bookmarks
        }
        db.close()

    def get(self, bookmark_id):
        return self.bookmarks.get(bookmark_id)

    async def add(self, author_id, author_name, description, team_code):
        if len(self.get_my_bookmarks(author_id)) >= MAX_BOOKMARKS:
            raise BookmarkError(f'You have reached the maximum amount of {MAX_BOOKMARKS} bookmarks.'
                                f' Please consider deleting some using `!bookmark delete <id>`.')

        _id = self.generate_new_id(author_name)
        bookmark = {
            'id': _id,
            'author_id': str(author_id),
            'author_name': author_name,
            'description': description,
            'team_code': team_code,
            'created': datetime.datetime.utcnow(),
        }
        lock = asyncio.Lock()
        async with lock:
            self.bookmarks[_id] = bookmark
            db = DB()
            db.cursor.execute(
                'REPLACE INTO Bookmark (id, author_id, author_name, description, team_code) '
                'VALUES (?, ?, ?, ?, ?)',
                (_id,
                 author_id,
                 author_name,
                 description,
                 team_code,
                 ))
            db.commit()
            db.close()
        return _id

    async def remove(self, author_id, bookmark_id):
        if bookmark_id not in self.bookmarks:
            raise BookmarkError('The bookmark you are trying to delete does not exist.')
        elif str(author_id) != self.bookmarks[bookmark_id]['author_id']:
            raise BookmarkError('The bookmark you are trying to delete belongs to someone else.')
        lock = asyncio.Lock()
        async with lock:
            db = DB()
            db.cursor.execute('DELETE FROM Bookmark WHERE id = ?', (bookmark_id,))
            db.commit()
            db.close()
            del (self.bookmarks[bookmark_id])

    def get_my_bookmarks(self, author_id):
        return [t for t in self.bookmarks.values() if str(author_id) == t['author_id']]

    def __len__(self):
        return len(self.bookmarks)

    def __iter__(self):
        yield from self.bookmarks.values()

    def generate_new_id(self, author_name):
        hashids = Hashids(salt=author_name)
        offset = 0
        while True:
            _id = hashids.encode(len(self.bookmarks) + offset).lower()
            if _id not in self.bookmarks:
                return _id
            offset += 1
