# -*- coding: utf-8 -*-

# Copyright(C) 2012  Romain Bignon
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

from weboob.capabilities.housing import Query, POSTS_TYPES, ADVERT_TYPES
from weboob.tools.test import BackendTest
from weboob.tools.capabilities.housing.housing_test import HousingTest


class PapTest(BackendTest, HousingTest):
    MODULE = 'pap'

    FIELDS_ALL_HOUSINGS_LIST = [
        "id", "type", "advert_type", "house_type", "url", "title", "area",
        "cost", "currency", "utilities", "location", "text"
    ]
    FIELDS_ANY_HOUSINGS_LIST = [
        "photos",
        "station",
    ]
    FIELDS_ALL_SINGLE_HOUSING = [
        "id", "url", "type", "advert_type", "house_type", "title", "area",
        "cost", "currency", "utilities", "date", "location", "text",
        "phone"
    ]
    FIELDS_ANY_SINGLE_HOUSING = [
        "photos",
        "rooms",
        "bedrooms",
        "station"
    ]

    def test_pap_rent(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 1500
        query.type = POSTS_TYPES.RENT
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
        self.check_against_query(query)

    def test_pap_sale(self):
        query = Query()
        query.area_min = 20
        query.type = POSTS_TYPES.SALE
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
        self.check_against_query(query)

    def test_pap_furnished_rent(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 1500
        query.type = POSTS_TYPES.FURNISHED_RENT
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
        self.check_against_query(query)

    def test_pap_viager(self):
        query = Query()
        query.type = POSTS_TYPES.VIAGER
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)
        # Remove rooms from the tested fields as viager never have them
        self.FIELDS_ANY_HOUSINGS_LIST = [
            "photos",
            "station",
            "bedrooms"
        ]
        self.FIELDS_ANY_SINGLE_HOUSING = [
            "photos",
            "bedrooms",
            "station"
        ]
        self.check_against_query(query)

    def test_pap_professional(self):
        query = Query()
        query.area_min = 20
        query.cost_max = 900
        query.type = POSTS_TYPES.RENT
        query.advert_types = [ADVERT_TYPES.PROFESSIONAL]
        query.cities = []
        for city in self.backend.search_city('paris'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = list(self.backend.search_housings(query))
        self.assertEqual(len(results), 0)
