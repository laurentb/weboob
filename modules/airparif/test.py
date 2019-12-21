# -*- coding: utf-8 -*-

# Copyright(C) 2019      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals


from weboob.tools.test import BackendTest


class AirparifTest(BackendTest):
    MODULE = 'airparif'

    def test_gauges(self):
        all_gauges = list(self.backend.iter_gauges())
        paris_gauges = list(self.backend.iter_gauges(pattern='paris'))
        self.assertTrue(all_gauges)
        self.assertTrue(paris_gauges)

        self._check_gauge(all_gauges[0])

    def _check_gauge(self, g):
        self.assertTrue(g.id)
        self.assertTrue(g.name)
        self.assertTrue(g.city)
        self.assertTrue(g.object)
        self.assertTrue(g.sensors)

        self._check_sensor(g.sensors[0], g)

    def _check_sensor(self, s, g):
        self.assertTrue(s.id)
        self.assertTrue(s.name)
        self.assertTrue(s.unit)
        self.assertTrue(s.gaugeid == g.id)

        self.assertTrue(s.lastvalue.date)
        self.assertTrue(s.lastvalue.level)

        self.assertTrue(s.geo.latitude)
        self.assertTrue(s.geo.longitude)

        self.assertTrue(s.location.street)
        self.assertTrue(s.location.city)
        self.assertTrue(s.location.region)
        self.assertTrue(s.location.country)
        self.assertTrue(s.location.postal_code)
