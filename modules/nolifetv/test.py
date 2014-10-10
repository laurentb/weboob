# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon
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
from weboob.capabilities.video import BaseVideo


class NolifeTVTest(BackendTest):
    MODULE = 'nolifetv'

    def test_search(self):
        l = list(self.backend.search_videos('nolife'))
        self.assertTrue(len(l) > 0)
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and v.url.startswith('http://'), 'URL for video "%s" not found: %s' % (v.id, v.url))

    def test_latest(self):
        l = list(self.backend.iter_resources([BaseVideo], [u'latest']))
        assert len(l) > 0
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and v.url.startswith('http://'), 'URL for video "%s" not found: %s' % (v.id, v.url))
