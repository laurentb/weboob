# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013 Romain Bignon, Laurent Bachelier
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
from weboob.capabilities.video import BaseVideo

import requests


class YoutubeTest(BackendTest):
    MODULE = 'youtube'

    def test_search(self):
        l = list(self.backend.search_videos('lol'))
        self.assertTrue(len(l) > 0)
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and v.url.startswith('https://'), 'URL for video "%s" not found: %s' % (v.id, v.url))
        assert self.backend.get_video(v.shorturl)
        requests.get(v.url, stream=True)

    def test_latest(self):
        l = list(self.backend.iter_resources([BaseVideo], [u'latest']))
        assert len(l) > 0

    def test_drm(self):
        v = self.backend.get_video('http://youtu.be/UxxajLWwzqY')
        self.backend.fillobj(v, ('url',))
        assert len(v.url)

        try:
            requests.get(v.url, stream=True)
        except:
            self.fail("can't open url %s" % v.url)

    def test_weirdchars(self):
        v = self.backend.get_video('https://www.youtube.com/watch?v=BaW_jenozKc')
        self.backend.fillobj(v, ('title', 'url',))
        assert v.title
