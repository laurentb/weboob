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

from weboob.capabilities.paste import PasteNotFound

class PastealaconTest(BackendTest):
    BACKEND = 'pastealacon'

    def _get_paste(self, _id):
        # html method
        p = self.backend.get_paste(_id)
        self.backend.fillobj(p, ['title'])
        assert p.title == 'ouiboube'
        assert p.page_url.startswith('http://pastealacon.com/')
        assert u'héhéhé' in p.contents

        # raw method
        p = self.backend.get_paste(_id)
        self.backend.fillobj(p, ['contents'])
        assert p.title is NotLoaded
        assert p.page_url.startswith('http://pastealacon.com/')
        assert u'héhéhé' in p.contents

    def test_post(self):
        p = self.backend.new_paste(None, title='ouiboube', contents=u'Weboob Test héhéhé')
        self.backend.post_paste(p)
        assert p.id
        self.backend.fill_paste(p, ['title'])
        assert p.title == 'ouiboube'
        assert p.id in p.page_url

        # test all get methods from the Paste we just created
        self._get_paste(p.id)

        # same but from the full URL
        self._get_paste('http://pastealacon.com/'+p.id)

    def test_spam(self):
        p = self.backend.new_paste(None, title='viagra', contents='http://example.com/')
        self.assertRaises(BrowserUnavailable, self.backend.post_paste, p)

    def test_notfound(self):
        for _id in ('424242424242424242424242424242424242', 'http://pastealacon.com/424242424242424242424242424242424242'):
            # html method
            p = self.backend.get_paste(_id)
            self.assertRaises(PasteNotFound, self.backend.fillobj, p, ['title'])

            # raw method
            p = self.backend.get_paste(_id)
            self.assertRaises(PasteNotFound, self.backend.fillobj, p, ['contents'])

    def test_checkurl(self):
        # call with an URL we can't handle with this backend
        assert self.backend.get_paste('http://pastebin.com/nJG9ZFG8') is None
        # same even with correct domain (IDs are numeric)
        assert self.backend.get_paste('http://pastealacon.com/nJG9ZFG8') is None
        assert self.backend.get_paste('nJG9ZFG8') is None
