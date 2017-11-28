# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
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

from __future__ import unicode_literals

import itertools

from weboob.tools.test import BackendTest
from weboob.capabilities.housing import Query, POSTS_TYPES, ADVERT_TYPES


class FonciaTest(BackendTest):
    MODULE = 'foncia'

    def test_city(self):
        # Paris search has multiple entries in the response
        self.assertGreater(len(list(self.backend.search_city(u'Paris'))), 1)

        # Postal code query has a single entry in the response
        montrouge = list(self.backend.search_city(u'92120'))
        self.assertEqual(len(montrouge), 1)
        self.assertIn("Montrouge", montrouge[0].name)

        # Also check everything is working with departements
        loiret_dept = list(self.backend.search_city(u'Loiret'))
        self.assertEqual(len(loiret_dept), 1)
        self.assertIn("Loiret", loiret_dept[0].name)

    def test_search_housings_sale(self):
        query = Query()
        query.cities = []
        query.type = POSTS_TYPES.SALE
        for city in self.backend.search_city('92120'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = list(itertools.islice(self.backend.search_housings(query), 0, 20))
        self.assertGreater(len(results), 0)
        obj = self.backend.fillobj(results[0])
        self.assertTrue(obj.url is not None, 'Missing url for "%s"' % (obj.id))

    def test_search_housings_rent(self):
        query = Query()
        query.cities = []
        query.type = POSTS_TYPES.RENT
        for city in self.backend.search_city('92120'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = list(itertools.islice(self.backend.search_housings(query), 0, 20))
        self.assertGreater(len(results), 0)
        obj = self.backend.fillobj(results[0])
        self.assertTrue(obj.url is not None, 'Missing url for "%s"' % (obj.id))

    def test_search_housings_personal(self):
        query = Query()
        query.cities = []
        query.type = POSTS_TYPES.RENT
        query.advert_types = [ADVERT_TYPES.PERSONAL]
        for city in self.backend.search_city('92120'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = list(itertools.islice(self.backend.search_housings(query), 0, 20))
        self.assertEqual(len(results), 0)

    def test_get_housing(self):
        query = Query()
        query.cities = []
        query.type = POSTS_TYPES.RENT
        for city in self.backend.search_city('92120'):
            city.backend = self.backend.name
            query.cities.append(city)

        result = next(self.backend.search_housings(query))
        obj = self.backend.fillobj(result)
        housing = self.backend.get_housing(result.id)
        obj = self.backend.fillobj(housing)
        self.assertTrue(obj.url is not None, 'Missing url for "%s"' % (obj.id))
