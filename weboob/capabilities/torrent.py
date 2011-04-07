# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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

from datetime import datetime

from .base import IBaseCap, CapBaseObject, NotLoaded


__all__ = ['ICapTorrent', 'Torrent']


class Torrent(CapBaseObject):
    def __init__(self, id, name, date=NotLoaded, size=NotLoaded, url=NotLoaded,
                       seeders=NotLoaded, leechers=NotLoaded, files=NotLoaded,
                       description=NotLoaded):
        CapBaseObject.__init__(self, id)
        self.add_field('name', basestring, name)
        self.add_field('size', (int,long,float), size)
        self.add_field('date', datetime, date)
        self.add_field('url', basestring, url)
        self.add_field('seeders', int, seeders)
        self.add_field('leechers', int, leechers)
        self.add_field('files', list, files)
        self.add_field('description', basestring, description)

class ICapTorrent(IBaseCap):
    def iter_torrents(self, pattern):
        raise NotImplementedError()

    def get_torrent(self, _id):
        raise NotImplementedError()

    def get_torrent_file(self, _id):
        raise NotImplementedError()
