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

from nose.plugins.skip import SkipTest
from weboob.tools.test import BackendTest
from weboob.capabilities.audio import BaseAudio


class GroovesharkTest(BackendTest):
    BACKEND = 'grooveshark'

    def test_grooveshark_audio_search(self):
        result = list(self.backend.search_audio("Gronibard"))
        self.assertTrue(len(result) > 0)
        v = result[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url is not None, 'URL for audio "%s" not found: %s' % (v.id, v.url))

    def test_grooveshark_user_playlist_not_logged(self):
        if self.backend.browser.is_logged():
            raise SkipTest("User credentials defined")
        l1 = list(self.backend.iter_resources([BaseAudio], []))
        assert len(l1) == 0

    def test_grooveshark_user_playlist_logged(self):
        if not self.backend.browser.is_logged():
            raise SkipTest("User credentials not defined")
        l1 = list(self.backend.iter_resources([BaseAudio], []))
        assert len(l1)

    def test_grooveshark_album_search(self):
        result = list(self.backend.search_album("Gronibard"))
        self.assertTrue(len(result) > 0)
        v = result[0]
        self.backend.fillobj(v)
        assert len(v.tracks_list)

    def test_grooveshark_playlist_search(self):
        result = list(self.backend.search_playlist("johann"))
        self.assertTrue(len(result) > 0)
        v = result[0]
        self.backend.fillobj(v)
        assert len(v.tracks_list)
