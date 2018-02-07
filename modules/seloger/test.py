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
from weboob.capabilities.housing import Query, POSTS_TYPES, ADVERT_TYPES
from weboob.tools.test import BackendTest


class SeLogerTest(BackendTest):
    MODULE = 'seloger'

    def check_housing_lists(self, query):
        results = list(itertools.islice(
            self.backend.search_housings(query),
            20
        ))
        self.assertTrue(len(results) > 0)

        if query.type == POSTS_TYPES.FURNISHED_RENT:
            # Seloger does not let us discriminate between these.
            type = POSTS_TYPES.RENT
        else:
            type = query.type

        self.assertTrue(any(x.photos for x in results))

        # TODO: No tests for rooms, bedrooms

        for x in results:
            self.assertIn(x.house_type, [
                str(y) for y in query.house_types
            ])
            self.assertTrue(x.text)
            self.assertTrue(x.cost)
            self.assertTrue(x.currency)
            self.assertEqual(x.type, type, 'Wrong type on %s' % x.url)
            self.assertTrue(x.id)
            self.assertTrue(x.area)
            self.assertTrue(x.title)
            self.assertTrue(x.date)
            self.assertTrue(x.location)
            self.assertIn(x.advert_type, query.advert_types)
            for photo in x.photos:
                self.assertRegexpMatches(photo.url, r'^http(s?)://')

        return results

    def check_single_housing(self, housing, advert_type):
        self.assertTrue(housing.id)
        self.assertTrue(housing.type)
        self.assertEqual(housing.advert_type, advert_type)
        self.assertTrue(housing.house_type)
        self.assertTrue(housing.title)
        self.assertTrue(housing.cost)
        self.assertTrue(housing.currency)
        self.assertTrue(housing.area)
        self.assertTrue(housing.date)
        self.assertTrue(housing.location)
        self.assertTrue(housing.rooms)
        self.assertTrue(housing.phone)
        self.assertTrue(housing.text)
        self.assertTrue(housing.url)
        self.assertTrue(len(housing.photos) > 0)
        for photo in housing.photos:
            self.assertRegexpMatches(photo.url, r'^http(s?)://')
        # No tests for DPE, bedrooms, station

    def test_seloger_rent(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 1500
        query.type = POSTS_TYPES.RENT
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = self.check_housing_lists(query)

        housing = self.backend.get_housing(results[0].id)
        self.check_single_housing(housing, results[0].advert_type)
        self.assertTrue(housing.location)

    def test_seloger_sale(self):
        query = Query()
        query.area_min = 20
        query.type = POSTS_TYPES.SALE
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = self.check_housing_lists(query)

        housing = self.backend.get_housing(results[0].id)
        self.check_single_housing(housing, results[0].advert_type)

    def test_seloger_furnished_rent(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 1500
        query.type = POSTS_TYPES.FURNISHED_RENT
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = self.check_housing_lists(query)

        housing = self.backend.get_housing(results[0].id)
        self.check_single_housing(housing, results[0].advert_type)
        self.assertTrue(housing.location)

    def test_seloger_viager(self):
        query = Query()
        query.type = POSTS_TYPES.VIAGER
        query.cities = []
        for city in self.backend.search_city('85'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = self.check_housing_lists(query)

        housing = self.backend.get_housing(results[0].id)
        self.check_single_housing(housing, results[0].advert_type)

    def test_seloger_rent_personal(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 1500
        query.type = POSTS_TYPES.RENT
        query.advert_types = [ADVERT_TYPES.PERSONAL]
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = self.check_housing_lists(query)

        housing = self.backend.get_housing(results[0].id)
        self.check_single_housing(housing, results[0].advert_type)
