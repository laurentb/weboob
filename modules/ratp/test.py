# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
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


class RATPTest(BackendTest):
    MODULE = 'ratp'

    def test_ratp_gauges(self):
        l = list(self.backend.iter_gauges())
        assert len(l) == 26

    def test_ratp_gauges_filter(self):
        l = list(self.backend.iter_gauges(pattern="T3A"))
        assert len(l) == 1

    def test_ratp_sensors(self):
        l = list(self.backend.iter_sensors("ligne_metro_4"))
        assert len(l) == 1

    def test_ratp_status(self):
        m = self.backend.get_last_measure("ligne_metro_4_sensor")
        assert m.level <= 0.0
