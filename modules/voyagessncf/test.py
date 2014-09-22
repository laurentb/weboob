# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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


class VoyagesSNCFTest(BackendTest):
    MODULE = 'voyagessncf'

    def test_stations(self):
        stations = list(self.backend.iter_station_search('paris'))
        self.assertTrue(len(stations) > 0)
        self.assertTrue('Paris Massy' in stations[-1].name)

    def test_departures(self):
        departure = list(self.backend.iter_station_search('paris'))[0]
        arrival = list(self.backend.iter_station_search('lyon'))[0]

        prices = list(self.backend.iter_station_departures(departure.id, arrival.id))
        self.assertTrue(len(prices) > 0)
