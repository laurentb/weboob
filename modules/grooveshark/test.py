# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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


from weboob.tools.test import BackendTest
from weboob.capabilities.audio import BaseAudio


class GroovesharkTest(BackendTest):
    BACKEND = 'grooveshark'

    def test_grooveshark_audio_search(self):
        result = list(self.backend.search_audios("Loic Lantoine"))
        self.assertTrue(len(result) > 0)

    def test_grooveshark_user_playlist(self):
        l1 = list(self.backend.iter_resources([BaseAudio], [u'playlists']))
        assert len(l1)
        c = l1[0]
        l2 = list(self.backend.iter_resources([BaseAudio], c.split_path))
        assert len(l2)
        v = l2[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url is not None, 'URL for audio "%s" not found: %s' % (v.id, v.url))

    def test_grooveshark_album_search(self):
        l1 = list(self.backend.iter_resources([BaseAudio], [u'albums', u'live']))
        assert len(l1)
        c = l1[0]
        l2 = list(self.backend.iter_resources([BaseAudio], c.split_path))
        assert len(l2)
        v = l2[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url is not None, 'URL for audio "%s" not found: %s' % (v.id, v.url))
