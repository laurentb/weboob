# -*- coding: utf-8 -*-

# Copyright(C) 2011 Laurent Bachelier
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
from weboob.capabilities.base import NotLoaded
from weboob.capabilities.paste import PasteNotFound

class PastebinTest(BackendTest):
    BACKEND = 'pastebin'

    def test_get_paste(self):
        for _id in ('7HmXwzyt', 'http://pastebin.com/7HmXwzyt'):
            # html method
            p = self.backend.get_paste(_id)
            self.backend.fillobj(p, ['title'])
            assert p.title == 'plop'
            assert p.page_url == 'http://pastebin.com/7HmXwzyt'
            assert p.contents == 'prout'
            assert p.public is True

            # raw method
            p = self.backend.get_paste(_id)
            self.backend.fillobj(p, ['contents'])
            assert p.title is NotLoaded
            assert p.page_url == 'http://pastebin.com/7HmXwzyt'
            assert p.contents == 'prout'
            assert p.public is NotLoaded

    def test_post(self):
        p = self.backend.new_paste(None, title='ouiboube', contents='Weboob Test', public=True)
        self.backend.post_paste(p)
        assert p.id
        self.backend.fill_paste(p, ['title'])
        assert p.title == 'ouiboube'
        assert p.id in p.page_url
        assert p.public is True

    def test_specialchars(self):
        # post a paste and get the contents through the HTML response
        p1 = self.backend.new_paste(None, title='ouiboube', contents=u'Weboob <test>¿¡', public=False)
        self.backend.post_paste(p1)
        assert p1.id
        assert p1.public is False

        # this should use the raw method to get the contents
        p2 = self.backend.get_paste(p1.id)
        self.backend.fillobj(p2, ['contents'])
        assert p2.contents == p1.contents
        assert p2.public is NotLoaded

    def test_notfound(self):
        for _id in ('weboooooooooooooooooooooooooob', 'http://pastebin.com/weboooooooooooooooooooooooooob'):
            # html method
            p = self.backend.get_paste(_id)
            self.assertRaises(PasteNotFound, self.backend.fillobj, p, ['title'])

            # raw method
            p = self.backend.get_paste(_id)
            self.assertRaises(PasteNotFound, self.backend.fillobj, p, ['contents'])

    def test_checkurl(self):
        # call with an URL we can't handle with this backend
        assert self.backend.get_paste('http://pastealacon.com/1') is None

    def test_can_post(self):
        assert self.backend.can_post(public=None) > 0
        assert self.backend.can_post(public=True) > 0
        assert self.backend.can_post(public=False) > 0
