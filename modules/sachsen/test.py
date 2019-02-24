# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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
from weboob.capabilities.base import find_object


class SachsenTest(BackendTest):
    MODULE = 'sachsen'

    def test_sachsen(self):
        l = list(self.backend.iter_gauges())
        self.assertTrue(len(l) > 0)

        gauge = find_object(l, id=u'501060')

        sensors = list(self.backend.iter_sensors(gauge))
        self.assertTrue(len(sensors) > 0)

        for sensor in sensors:
            self.assertTrue(sensor.lastvalue.level > 0)

        sensor = sensors[0]

        history = list(self.backend.iter_gauge_history(sensor))
        self.assertTrue(len(history) > 0)

        self.assertTrue(self.backend.get_last_measure(sensor) is not None)
