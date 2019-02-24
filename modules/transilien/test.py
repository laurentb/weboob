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

import datetime

from weboob.capabilities.travel import RoadmapFilters
from weboob.tools.test import BackendTest


class TransilienTest(BackendTest):
    MODULE = 'transilien'

    def test_stations(self):
        stations = list(self.backend.iter_station_search('aul'))
        self.assertTrue(len(stations) > 0)

    def test_departures(self):
        stations = list(self.backend.iter_station_search('paris'))
        self.assertTrue(len(stations) > 0)
        list(self.backend.iter_station_departures(stations[0].id))

    def test_roadmap(self):
        filters = RoadmapFilters()
        roadmap = list(self.backend.iter_roadmap('aul', u'aub', filters))
        self.assertTrue(len(roadmap) > 0)

        filters.arrival_time = datetime.datetime.now() + datetime.timedelta(days=1)
        roadmap = list(self.backend.iter_roadmap('aul', u'bag', filters))
        self.assertTrue(len(roadmap) > 0)

        filters.departure_time = datetime.datetime.now() + datetime.timedelta(days=1)
        roadmap = list(self.backend.iter_roadmap('gare du nord', u'stade de boulogne', filters))
        self.assertTrue(len(roadmap) > 0)
