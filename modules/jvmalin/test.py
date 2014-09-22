# -*- coding: utf-8 -*-

# Copyright(C) 2013 Alexandre Lissy
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

import datetime

from weboob.capabilities.travel import RoadmapFilters
from weboob.tools.test import BackendTest


class JVMalinTest(BackendTest):
    MODULE = 'jvmalin'

    def test_roadmap_cities(self):
        filters = RoadmapFilters()
        roadmap = list(self.backend.iter_roadmap('Tours', 'Orléans', filters))
        self.assertTrue(len(roadmap) > 0)

    def test_roadmap_stop_intercity(self):
        filters = RoadmapFilters()
        roadmap = list(self.backend.iter_roadmap('Tours Jean-Jaurès', 'Orléans', filters))
        self.assertTrue(len(roadmap) > 0)

    def test_roadmap_stop_intracity(self):
        filters = RoadmapFilters()
        roadmap = list(self.backend.iter_roadmap('Tours Jean-Jaurès', 'Polytech Tours', filters))
        self.assertTrue(len(roadmap) > 0)

    def test_roadmap_stop_intracity2(self):
        filters = RoadmapFilters()
        roadmap = list(self.backend.iter_roadmap('J.P.Rameau', 'Polytech Tours', filters))
        self.assertTrue(len(roadmap) > 0)

    def test_roadmap_names(self):
        filters = RoadmapFilters()
        roadmap = list(self.backend.iter_roadmap('Artannes Mairie', 'Château de Blois', filters))
        self.assertTrue(len(roadmap) > 0)

    def test_roadmap_long(self):
        filters = RoadmapFilters()
        roadmap = list(self.backend.iter_roadmap('Chartres', 'Ballan-Miré', filters))
        self.assertTrue(len(roadmap) > 0)

    def test_roadmap_departure(self):
        filters = RoadmapFilters()
        filters.departure_time = datetime.datetime.now() + datetime.timedelta(days=1)
        roadmap = list(self.backend.iter_roadmap('Chartres', 'Ballan-Miré', filters))
        self.assertTrue(len(roadmap) > 0)

    def test_roadmap_arrival(self):
        filters = RoadmapFilters()
        filters.arrival_time = datetime.datetime.now() + datetime.timedelta(days=1)
        roadmap = list(self.backend.iter_roadmap('Chartres', 'Ballan-Miré', filters))
        self.assertTrue(len(roadmap) > 0)
