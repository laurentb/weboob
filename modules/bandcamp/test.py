# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

from weboob.tools.test import BackendTest


class BandcampTest(BackendTest):
    MODULE = 'bandcamp'

    def test_search_audio(self):
        file = next(self.backend.search_audio('la nuit des sales bêtes'))
        self.assertEqual('audio.degelite.la-nuit-des-sales-b-tes', file.id)
        assert file.duration
        self.assertEqual('la nuit des sales bêtes', file.title.lower())
        self.assertEqual('casio judiciaire', file.author.lower())
        assert file.url
        self.assertEqual('audio/mpeg', self.backend.browser.open(file.url, stream=True).headers['content-type'])

    def test_search_album(self):
        album = next(self.backend.search_album('disco quake'))
        assert album.id.startswith('album.')
        self.assertEqual('202project', album.author.lower())
        self.assertEqual('disco quake', album.title.lower())
        self.assertEqual(12, len(album.tracks_list))
        self.assertEqual('https://202project.bandcamp.com/album/disco-quake', album.url)

    def test_get(self):
        album = self.backend.get_album('album.casiojudiciaire.d-mo')
        assert album

        file = self.backend.get_audio('audio.casiojudiciaire.travaux-pubiques')
        assert file
