# -*- coding: utf-8 -*-

# Copyright(C) 2018 Julien Veyssier
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from weboob.tools.test import BackendTest
from weboob.capabilities.base import NotLoaded


class YggtorrentTest(BackendTest):
    MODULE = 'yggtorrent'

    def test_torrent(self):
        torrents = list(self.backend.iter_torrents('spiderman'))[:10]
        for torrent in torrents:
            assert torrent.url
            assert torrent.id
            assert torrent.name
            assert torrent.description is NotLoaded
            full_torrent = self.backend.get_torrent(torrent.id)
            assert full_torrent.description is not NotLoaded

