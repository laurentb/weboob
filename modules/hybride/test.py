# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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

from weboob.tools.test import BackendTest, SkipTest


class HybrideTest(BackendTest):
    MODULE = 'hybride'

    def test_hybride_list(self):
        if datetime.now() > datetime(datetime.now().year, 6, 30) and\
           datetime.now() < datetime(datetime.now().year, 9, 15):
            raise SkipTest("Fermeture estivale")
        l = list(self.backend.list_events(datetime.now()))
        assert len(l)
        event = self.backend.get_event(l[0].id)
        self.assertTrue(event.url, 'URL for event "%s" not found: %s' % (event.id, event.url))
