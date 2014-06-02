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
from weboob.capabilities.base import CapBaseObject


class TwitterTest(BackendTest):
    BACKEND = 'twitter'

    def test_twitter_logged(self):
        if self.backend.browser.username:
            assert(self.backend.browser.get_me())
        else:
            raise SkipTest("User credentials not defined")

    def test_twitter_list(self):
        if self.backend.browser.username:
            l = list(self.backend.iter_threads())
            assert len(l)
            thread = self.backend.get_thread(l[0].id)
            assert len(thread.root.content)
        else:
            raise SkipTest("User credentials not defined")

    def test_ls_me(self):
        if self.backend.browser.username:
            l = list(self.backend.iter_resources([CapBaseObject], ['me']))
            assert len(l)
            thread = self.backend.get_thread(l[0].id)
            assert len(thread.root.content)
        else:
            raise SkipTest("User credentials not defined")

    def test_ls_search(self):
        l = list(self.backend.iter_resources([CapBaseObject], ['search', 'weboob']))
        assert len(l)
        thread = self.backend.get_thread(l[0].id)
        assert len(thread.root.content)

    def test_ls_hashtag(self):
        l = list(self.backend.iter_resources([CapBaseObject], ['hashtags', 'weboob']))
        assert len(l)
        thread = self.backend.get_thread(l[0].id)
        assert len(thread.root.content)

    def test_ls_profils(self):
        l = list(self.backend.iter_resources([CapBaseObject], ['profils', 'jf_cope']))
        assert len(l)
        thread = self.backend.get_thread(l[0].id)
        assert len(thread.root.content)

    def test_ls_trend(self):
        l = list(self.backend.iter_resources([CapBaseObject], ['trendy']))
        assert len(l)
        l1 = list(self.backend.iter_resources([CapBaseObject], ['trendy', u'%s' % l[0].split_path[0]]))
        assert len(l1)
        thread = self.backend.get_thread(l1[0].id)
        assert len(thread.root.content)
