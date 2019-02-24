# -*- coding: utf-8 -*-

# Copyright(C) 2011-2014 Laurent Bachelier
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


from weboob.tools.test import BackendTest, skip_without_config
from weboob.capabilities.base import NotLoaded

from weboob.capabilities.paste import PasteNotFound


class PastealaconTest(BackendTest):
    MODULE = 'pastealacon'

    def _get_paste(self, _id):
        # html method
        p = self.backend.get_paste(_id)
        self.backend.fillobj(p, ['title'])
        assert p.title == u'ouiboube'
        assert p.page_url.startswith('http://paste.alacon.org/')
        assert u'héhéhé' in p.contents
        assert p.public is True

        # raw method
        p = self.backend.get_paste(_id)
        self.backend.fillobj(p, ['contents'])
        assert p.title is NotLoaded
        assert p.page_url is None
        assert u'héhéhé' in p.contents
        assert p.public is True

    @skip_without_config()
    def test_post(self):
        p = self.backend.new_paste(None, title=u'ouiboube', contents=u'Weboob Test héhéhé')
        self.backend.post_paste(p, max_age=3600*24)
        assert p.id
        self.backend.fill_paste(p, ['title'])
        assert p.title == 'ouiboube'
        assert p.id in p.page_url
        assert p.public is True

        # test all get methods from the Paste we just created
        self._get_paste(p.id)

        # same but from the full URL
        self._get_paste('http://paste.alacon.org/'+p.id)

    def test_spam(self):
        p = self.backend.new_paste(None, title=u'viagra', contents=u'http://example.com/')
        with self.assertRaises(Exception) as cm:
            self.backend.post_paste(p)
            self.assertEqual(cm.message, "Detected as spam and unable to handle the captcha")

    def test_notfound(self):
        for _id in ('424242424242424242424242424242424242',
                    'http://paste.alacon.org/424242424242424242424242424242424242'):
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
        assert self.backend.get_paste('http://paste.alacon.org/nJG9ZFG8') is None
        assert self.backend.get_paste('nJG9ZFG8') is None

    def test_can_post(self):
        assert 0 == self.backend.can_post(u'hello', public=False)
        assert 1 <= self.backend.can_post(u'hello', public=True)
        assert 0 == self.backend.can_post(u'hello', public=True, max_age=600)
        assert 1 <= self.backend.can_post(u'hello', public=True, max_age=3600*24)
        assert 1 <= self.backend.can_post(u'hello', public=True, max_age=3600*24*3)
        assert 1 <= self.backend.can_post(u'hello', public=True, max_age=False)
        assert 1 <= self.backend.can_post(u'hello', public=None, max_age=False)
        assert 1 <= self.backend.can_post(u'hello', public=True, max_age=3600*24*40)
        assert 1 <= self.backend.can_post(u'héhé', public=True)
        assert 0 == self.backend.can_post(u'hello ♥', public=True)
