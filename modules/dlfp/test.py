# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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


from datetime import datetime

from weboob.tools.test import BackendTest, skip_without_config
from .browser import DLFP


class DLFPTest(BackendTest):
    MODULE = 'dlfp'

    def __init__(self, *args, **kwargs):
        super(DLFPTest, self).__init__(*args, **kwargs)
        DLFP.DOMAIN = 'alpha.linuxfr.org'

    def test_new_messages(self):
        feeds = {}
        for name, feed in self.backend.FEEDS.items():
            feeds[name] = feed.replace('//linuxfr.org', '//alpha.linuxfr.org')
        self.backend.FEEDS = feeds

        for message in self.backend.iter_unread_messages():
            pass

    @skip_without_config("username")
    def test_get_content(self):
        self.backend.get_content(u"Ceci-est-un-test")

    @skip_without_config("username")
    def test_push_content(self):
        content = self.backend.get_content(u"Ceci-est-un-test")
        content.content = "test " + str(datetime.now())
        self.backend.push_content(content, message="test weboob", minor=True)

    @skip_without_config("username")
    def test_content_preview(self):
        content = self.backend.get_content(u"Ceci-est-un-test")
        self.backend.get_content_preview(content)
