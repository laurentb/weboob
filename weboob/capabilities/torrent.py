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


from .base import IBaseCap


__all__ = ['ICapTorrent', 'Torrent']


class Torrent(object):
    def __init__(self, id, name, date=None, size=0.0, url=u'', seeders=0, leechers=0, files=[], description=u''):
        self.id = id
        self.name = name
        self.date = date
        self.size = size
        self.url = url
        self.seeders = seeders
        self.leechers = leechers
        self.files = files
        self.description = description


class ICapTorrent(IBaseCap):
    def iter_torrents(self, pattern):
        raise NotImplementedError()

    def get_torrent(self, _id):
        raise NotImplementedError()

    def get_torrent_file(self, _id):
        raise NotImplementedError()
