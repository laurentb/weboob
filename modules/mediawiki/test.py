# -*- coding: utf-8 -*-

# Copyright(C) 2011  Clément Schreiner
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

from datetime import datetime

from weboob.tools.test import BackendTest


class MediawikiTest(BackendTest):
    MODULE = 'mediawiki'

    def test_get_content(self):
        obj = self.backend.get_content(u"Project:Sandbox")
        assert len(obj.content) > 0

    def test_iter_revisions(self):
        for rev in zip(range(10), self.backend.iter_revisions(u"Project:Sandbox")):
            pass

    def test_push_content(self):
        content = self.backend.get_content(u"Project:Sandbox")
        content.content = "%s\nhello %s" % (content.content, datetime.now())
        # ^ warning: wikipedia seems to have blocked lines starting with "test"...
        self.backend.push_content(content, message="test weboob", minor=True)
        new_content = self.backend.get_content(u"Project:Sandbox")
        self.assertEquals(content.content, new_content.content)

    def test_content_preview(self):
        content = self.backend.get_content(u"Project:Sandbox")
        self.backend.get_content_preview(content)

    def test_search_image(self):
        it = iter(self.backend.search_file('logo'))
        for _, img in zip(range(3), it):
            assert img
            assert img.title
            assert img.ext
            assert img.page_url
            assert img.size
            if not img.url:
                img = self.backend.fillobj(img, ['url'])
            assert img.url
            assert img.thumbnail.url
