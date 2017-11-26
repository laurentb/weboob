# -*- coding: utf-8 -*-

# Copyright(C) 2017      Roger Philibert
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


class XHamsterTest(BackendTest):
    MODULE = 'xhamster'

    def test_search(self):
        vids = list(zip(range(30), self.backend.search_videos('fuck', nsfw=True)))
        assert vids
        for _, vid in vids:
            assert vid.id
            assert vid.title
            assert vid.duration
            assert vid.thumbnail.url

        old = vids[0][1]
        new = self.backend.get_video(old.id)
        assert new
        self.assertEquals(old.title, new.title)
        self.assertEquals(old.duration, new.duration)
        self.assertEquals(old.id, new.id)
        assert new.url

        self.backend.fillobj(old, ['url', 'thumbnail'])
        assert old.thumbnail.data
        self.assertEquals(old.url, new.url)
