# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from nose.plugins.skip import SkipTest
from weboob.tools.test import BackendTest


class FeedlyTest(BackendTest):
    BACKEND = 'feedly'

    def test_login(self):
        if self.backend.browser.username:
            list(self.backend.iter_threads())
        else:
            raise SkipTest("User credentials not defined")

    def test_feedly(self):
        self.backend.browser.username = None
        l1 = list(self.backend.iter_resources(None, ['Technologie', 'Korben']))
        assert len(l1)
        thread = self.backend.get_thread(l1[0].id)
        assert len(thread.root.content)
