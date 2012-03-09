# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon, Laurent Bachelier
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

from .base import IBaseCap, CapBaseObject


__all__ = ['ICapTorrent', 'Torrent']


class MagnetOnly(Exception):
    def __init__(self, magnet):
        self.magnet = magnet
        Exception.__init__(self, 'Only magnet URL is available')


class Torrent(CapBaseObject):
    def __init__(self, id, name):
        CapBaseObject.__init__(self, id)
        self.add_field('name', basestring, name)
        self.add_field('size', (int, long, float))
        self.add_field('date', datetime)
        self.add_field('url', basestring)
        self.add_field('magnet', basestring)
        self.add_field('seeders', int)
        self.add_field('leechers', int)
        self.add_field('files', list)
        self.add_field('description', basestring)
        self.add_field('filename', basestring)  # suggested name of the .torrent file


class ICapTorrent(IBaseCap):
    def iter_torrents(self, pattern):
        raise NotImplementedError()

    def get_torrent(self, _id):
        raise NotImplementedError()

    def get_torrent_file(self, _id):
        raise NotImplementedError()
