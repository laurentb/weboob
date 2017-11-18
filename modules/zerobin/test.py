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


class ZerobinTest(BackendTest):
    MODULE = 'zerobin'

    def test_writeread(self):
        p = self.backend.new_paste(_id=None, contents='weboob test')
        self.backend.browser.post_paste(p, 86400)

        assert p.url
        assert p.id
        assert p.title

        p2 = self.backend.get_paste(p.id)
        self.assertEqual(p2.contents, 'weboob test')
        assert p.url.startswith(self.backend.browser.BASEURL)
        self.assertEqual(p.url, p2.url)
        self.assertEqual(p.id, p2.id)

        p3 = self.backend.get_paste(p.url)
        self.assertEqual(p.id, p3.id)
