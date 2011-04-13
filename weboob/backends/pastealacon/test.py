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
from weboob.tools.browser import BrowserUnavailable
from .paste import PastealaconPaste

class PastealaconTest(BackendTest):
    BACKEND = 'pastealacon'

    def test_get_paste(self):
        # html method
        p = self.backend.get_paste('27184')
        self.backend.fillobj(p, ['title'])
        assert p.title == 'ouiboube'
        assert p.page_url == 'http://pastealacon.com/27184'
        assert u'coucou\r\ncoucou\r\nhéhéhé' == p.contents

        # raw method
        p = self.backend.get_paste('27184')
        self.backend.fillobj(p, ['contents'])
        assert p.title is NotLoaded
        assert p.page_url == 'http://pastealacon.com/27184'
        assert u'coucou\r\ncoucou\r\nhéhéhé' == p.contents

    def test_post(self):
        p = PastealaconPaste(None, title='ouiboube', contents='Weboob Test')
        self.backend.post_paste(p)
        assert p.id
        assert p.title == 'ouiboube'
        assert p.id in p.page_url

    def test_spam(self):
        p = PastealaconPaste(None, title='viagra', contents='http://example.com/')
        self.assertRaises(BrowserUnavailable, self.backend.post_paste, p)
