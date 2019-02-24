# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from weboob.tools.test import BackendTest
from weboob.capabilities.video import BaseVideo


class CanalPlusTest(BackendTest):
    MODULE = 'canalplus'

    def test_canalplus(self):
        l = list(self.backend.search_videos(u'guignol'))
        self.assertTrue(len(l) > 0)
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and (v.url.startswith('rtmp://') or v.url.startswith('http://')), 'URL for video "%s" not found: %s' % (v.id, v.url))

    def test_ls(self):
        l = list(self.backend.iter_resources((BaseVideo, ), []))
        self.assertTrue(len(l) > 0)

        l = list(self.backend.iter_resources((BaseVideo, ), [u'sport']))
        self.assertTrue(len(l) > 0)
