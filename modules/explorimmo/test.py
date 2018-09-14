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

from weboob.capabilities.housing import Query, ADVERT_TYPES, POSTS_TYPES
from weboob.tools.capabilities.housing.housing_test import HousingTest
from weboob.tools.test import BackendTest


class ExplorimmoTest(BackendTest, HousingTest):
    MODULE = 'explorimmo'

    FIELDS_ALL_HOUSINGS_LIST = [
        "id", "type", "advert_type", "house_type", "title", "location",
        "utilities", "text", "area", "url"
    ]
    FIELDS_ANY_HOUSINGS_LIST = [
        "photos", "cost", "currency"
    ]
    FIELDS_ALL_SINGLE_HOUSING = [
        "id", "url", "type", "advert_type", "house_type", "title", "area",
        "cost", "currency", "utilities", "date", "location", "text", "rooms",
        "details"
    ]
    FIELDS_ANY_SINGLE_HOUSING = [
        "bedrooms",
        "photos",
        "DPE",
        "GES",
        "phone"
    ]

    def test_explorimmo_rent(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 1500
        query.type = POSTS_TYPES.RENT
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
        self.check_against_query(query)

    def test_explorimmo_sale(self):
        query = Query()
        query.area_min = 20
        query.type = POSTS_TYPES.SALE
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
        self.check_against_query(query)

    def test_explorimmo_furnished_rent(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 1500
        query.type = POSTS_TYPES.FURNISHED_RENT
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
        self.check_against_query(query)

    def test_explorimmo_viager(self):
        query = Query()
        query.type = POSTS_TYPES.VIAGER
        query.cities = []
        for city in self.backend.search_city('85'):
            city.backend = self.backend.name
            query.cities.append(city)
        self.check_against_query(query)

    def test_explorimmo_personal(self):
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
