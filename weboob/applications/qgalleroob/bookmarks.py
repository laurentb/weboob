# -*- coding: utf-8 -*-

# Copyright(C) 2017 Vincent A
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from functools import wraps
from threading import RLock


def locked(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.lock:
            return func(self, *args, **kwargs)
    return wrapper


class BookmarkStorage(object):
    def __init__(self, storage):
        self.storage = storage
        self.lock = RLock()
        self.bookmarks = set(storage.get('bookmarks', default=[]))
        self.ignored = set(storage.get('ignored', default=[]))

    @locked
    def save(self):
        self.storage.set('bookmarks', list(self.bookmarks))
        self.storage.set('ignored', list(self.ignored))
        self.storage.save()

    @locked
    def is_bookmarked(self, id):
        return id in self.bookmarks

    @locked
    def is_ignored(self, id):
        return id in self.ignored

    @locked
    def add_bookmark(self, id):
        self.bookmarks.add(id)

    @locked
    def add_ignore(self, id):
        self.ignored.add(id)

