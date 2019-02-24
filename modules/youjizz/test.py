# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon
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


from weboob.tools.misc import limit
from weboob.tools.test import BackendTest
from weboob.capabilities.video import BaseVideo


class YoujizzTest(BackendTest):
    MODULE = 'youjizz'

    def test_search(self):
        self.assertTrue(len(self.backend.search_videos('anus', nsfw=False)) == 0)

        l = list(limit(self.backend.search_videos('anus', nsfw=True), 100))
        self.assertTrue(len(l) > 0)
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and v.url.startswith('http://'), 'URL for video "%s" not found: %s' % (v.id, v.url))
        r = self.backend.browser.open(v.url, stream=True)
        self.assertTrue(r.status_code == 200)

    def test_latest(self):
        l = list(limit(self.backend.iter_resources([BaseVideo], [u'latest_nsfw']), 100))
        self.assertTrue(len(l) > 0)
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and v.url.startswith('http://'), 'URL for video "%s" not found: %s' % (v.id, v.url))
