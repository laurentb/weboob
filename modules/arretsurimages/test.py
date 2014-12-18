# -*- coding: utf-8 -*-

# Copyright(C) 2013      franek
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

from weboob.capabilities.video import BaseVideo
from weboob.tools.test import BackendTest, SkipTest


class ArretSurImagesTest(BackendTest):
    MODULE = 'arretsurimages'

    def test_latest_arretsurimages(self):
        l = list(self.backend.iter_resources([BaseVideo], [u'latest']))
        assert len(l)
        if self.backend.browser.username != u'None':
            v = l[0]
            self.backend.fillobj(v, ('url',))
            self.assertTrue(v.url, 'URL for video "%s" not found' % (v.id))
        else:
            raise SkipTest("User credentials not defined")
