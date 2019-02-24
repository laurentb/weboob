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

from random import choice


class LimetorrentsTest(BackendTest):
    MODULE = 'limetorrents'

    def test_torrent(self):
        torrents = list(self.backend.iter_torrents('spiderman'))
        assert len(torrents) > 0
        for torrent in torrents:
            assert torrent.id
            assert torrent.name
            assert torrent.url

        # get the file of a random torrent
        # from the list (getting them all would be too long)
        if len(torrents):
            torrent = choice(torrents)
            self.backend.get_torrent_file(torrent.id)
