# -*- coding: utf-8 -*-

# Copyright(C) 2016      Vincent A
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


class PixabayTest(BackendTest):
    MODULE = 'pixabay'

    def test_search(self):
        it = self.backend.search_image('flower')
        img = it.next()
        assert img
        assert img.title
        assert self.backend.fillobj(img, ['data'])
        assert len(img.data)

        img = it.next()
        assert img
        assert img.title

    def test_get(self):
        img = self.backend.get_image(715540)
        assert img
