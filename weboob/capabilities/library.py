# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Jeremy Monnet
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime, date

from .collection import ICapCollection, CollectionNotFound
from .base import CapBaseObject


__all__ = ['ICapBook', 'Book']


class Book(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('name', basestring)
        self.add_field('author', basestring)
        self.add_field('location', basestring)
        self.add_field('date', (datetime, date)) # which may be the due date
        self.add_field('late', bool)


class ICapBook(ICapCollection):
    def iter_resources(self, objs, split_path):
        if Book in objs:
            if len(split_path) > 0:
                raise CollectionNotFound(split_path)

            return self.iter_books()

    def iter_books(self, pattern):
        raise NotImplementedError()

    def get_book(self, _id):
        raise NotImplementedError()

    def get_booked(self, _id):
        raise NotImplementedError()

    def get_rented(self, _id):
        raise NotImplementedError()

    def search_books(self, _string):
        raise NotImplementedError()
