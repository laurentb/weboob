# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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


class LogicimmoTest(BackendTest):
    MODULE = 'logicimmo'

    def check_housing_lists(self, query):
        results = list(itertools.islice(
            self.backend.search_housings(query),
            20
        ))
        self.assertTrue(len(results) > 0)

        self.assertTrue(any(x.photos for x in results))
        self.assertTrue(any(x.rooms for x in results))
        self.assertTrue(any(x.text for x in results))

        for x in results:
            self.assertIn(x.house_type, [
                str(y) for y in query.house_types
            ])
            for photo in x.photos:
                self.assertRegexpMatches(photo.url, r'^http(s?)://')
            self.assertTrue(x.date)
            self.assertTrue(x.location)
            self.assertTrue(x.area)
            self.assertTrue(x.cost)
            self.assertTrue(x.currency)
            self.assertTrue(x.title)
            self.assertEqual(x.type, query.type)
            self.assertTrue(x.id)
            self.assertTrue(x.url)
            self.assertIn(x.advert_type, query.advert_types)

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
        self.assertTrue(housing.text)
        self.assertTrue(housing.url)
        self.assertTrue(housing.photos)
        for photo in housing.photos:
            self.assertRegexpMatches(photo.url, r'^http(s?)://')
        self.assertTrue(housing.details.keys())
        # No tests for DPE, GES, rooms

    def test_logicimmo_rent(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 1500
        query.type = POSTS_TYPES.RENT
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
            if len(query.cities) == 3:
                break

        results = self.check_housing_lists(query)

        housing = self.backend.get_housing(results[0].id)
        self.backend.fillobj(housing, 'phone')
        self.check_single_housing(housing, results[0].advert_type)

    def test_logicimmo_sale(self):
        query = Query()
        query.area_min = 20
        query.type = POSTS_TYPES.SALE
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
            if len(query.cities) == 3:
                break

        results = self.check_housing_lists(query)

        housing = self.backend.get_housing(results[0].id)
        self.backend.fillobj(housing, 'phone')
        self.check_single_housing(housing, results[0].advert_type)

    def test_logicimmo_furnished_rent(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 1500
        query.type = POSTS_TYPES.FURNISHED_RENT
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
            if len(query.cities) == 3:
                break

        results = self.check_housing_lists(query)

        housing = self.backend.get_housing(results[0].id)
        self.backend.fillobj(housing, 'phone')
        self.check_single_housing(housing, results[0].advert_type)

    def test_logicimmo_viager(self):
        query = Query()
        query.type = POSTS_TYPES.VIAGER
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
            if len(query.cities) == 3:
                break

        results = self.check_housing_lists(query)

        housing = self.backend.get_housing(results[0].id)
        self.backend.fillobj(housing, 'phone')
        self.check_single_housing(housing, results[0].advert_type)

    def test_logicimmo_personal(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 900
        query.type = POSTS_TYPES.RENT
        query.advert_types = [ADVERT_TYPES.PERSONAL]
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = list(self.backend.search_housings(query))
        self.assertEqual(len(results), 0)
