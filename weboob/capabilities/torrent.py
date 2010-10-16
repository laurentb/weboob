# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

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
