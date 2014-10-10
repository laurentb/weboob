# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


class QuviTest(BackendTest):
    MODULE = 'quvi'

    def test_get_id(self):
        v = self.backend.get_video('youtube.BaW_jenozKc')
        assert len(v.url)
        assert len(v.title)
        assert (v.page_url == 'https://www.youtube.com/watch?v=BaW_jenozKc')

    def test_get_url(self):
        v = self.backend.get_video('https://www.youtube.com/watch?v=BaW_jenozKc')
        assert len(v.url)
        assert len(v.title)
        # did we retrieve more?
        assert len(v.ext)
        assert v.duration
        assert v.thumbnail
        assert v.page_url == 'https://www.youtube.com/watch?v=BaW_jenozKc'

    def test_get_shortened(self):
        v = self.backend.get_video('http://youtu.be/BaW_jenozKc')
        assert len(v.url)
        assert len(v.title)
        assert v.page_url.startswith('http://www.youtube.com/watch?v=BaW_jenozKc')
