# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Romain Bignon, Laurent Bachelier
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

from weboob.capabilities.video import BaseVideo
from weboob.tools.test import BackendTest


class PluzzTest(BackendTest):
    MODULE = 'francetelevisions'

    def test_search(self):
        # If the test fails, it might be good news!
        l = list(self.backend.search_videos("20h"))
        self.assertTrue(len(l) > 0)
        v = l[0]
        v = self.backend.fillobj(v, ('url',)) or v
        self.assertTrue(v.url, 'URL for video "%s" not found: %s' % (v.id, v.url))

    def test_categories(self):
        cat = list(self.backend.iter_resources([BaseVideo], []))
        self.assertTrue(len(cat) > 0)
        for c in cat:
            if c.split_path[-1].startswith('vid_'):
                videos = list(self.backend.iter_resources([BaseVideo], c.split_path))
                self.assertTrue(len(videos) > 0)
                v = videos[0]
                v = self.backend.fillobj(v, ('url',)) or v
                self.assertTrue(v.url, 'URL for video "%s" not found: %s' % (v.id, v.url))
                return
