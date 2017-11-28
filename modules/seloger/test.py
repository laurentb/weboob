# -*- coding: utf-8 -*-

# Copyright(C) 2012  Romain Bignon
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

import itertools
from weboob.capabilities.housing import Query, POSTS_TYPES
from weboob.tools.test import BackendTest


class SeLogerTest(BackendTest):
    MODULE = 'seloger'

    def test_seloger(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 1000
        query.type = POSTS_TYPES.RENT
        query.cities = []
        for city in self.backend.search_city(u'Ferté'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = list(itertools.islice(self.backend.search_housings(query), 0, 20))
        self.assertTrue(len(results) > 0)

        self.backend.fillobj(results[0], 'phone')
