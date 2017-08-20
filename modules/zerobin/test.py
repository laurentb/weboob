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

    def _test_read(self, url):
        p = self.backend.get_paste(url)
        self.assertEqual(p.contents, 'weboob test')
        self.assertEqual(p.id, url)
        self.assertEqual(p.url, url)
        assert p.title

    def test_read_0bin(self):
        self._test_read('https://0bin.net/paste/KLRN54Ie2i6bLSx7#+DRqWpm7bdtdxaSn6UMwKNQMpxEJt1EkbTjNvY4xM9i')

    def test_read_zerobin(self):
        self._test_read('https://zerobin.net/?2e0aa2e95f8d846b#QObWRdfQroCN7MsQ9y9zvEHk/KAoOAIZszo2LrJnCEA=')

    def _test_write(self, base):
        p = self.backend.new_paste(_id=None, contents='weboob test')
        old = self.backend.browser.BASEURL
        try:
            self.backend.browser.BASEURL = base
            self.backend.browser.post_paste(p, 86400)
        finally:
            self.backend.browser.BASEURL = old
        assert p.url
        assert p.id
        assert p.title

        p2 = self.backend.get_paste(p.url)
        self.assertEqual(p2.contents, 'weboob test')
        assert p.url.startswith(base)
        self.assertEqual(p.url, p2.url)
        self.assertEqual(p.id, p2.id)

    def test_write_0bin(self):
        self._test_write('https://0bin.net')

    def test_write_zerobin(self):
        self._test_write('https://zerobin.net')

    def test_write_current(self):
        self._test_write(self.backend.browser.BASEURL)
