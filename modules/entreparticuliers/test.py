# -*- coding: utf-8 -*-

# Copyright(C) 2015      Bezleputh
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
from weboob.capabilities.housing import (Query, POSTS_TYPES)
from weboob.tools.capabilities.housing.housing_test import HousingTest


class EntreparticuliersTest(BackendTest, HousingTest):
    MODULE = 'entreparticuliers'

    FIELDS_ALL_HOUSINGS_LIST = [
        "id", "type", "advert_type", "house_type", "title", "area",
        "cost", "currency", "utilities", "date", "location", "text"
    ]

    FIELDS_ANY_HOUSINGS_LIST = [
        "photos", "rooms"
    ]

    FIELDS_ALL_SINGLE_HOUSING = [
        "id", "url", "type", "advert_type", "house_type", "title", "area",
        "cost", "currency", "utilities", "date", "location", "text"
    ]

    FIELDS_ANY_SINGLE_HOUSING = [
        "photos", "phone", "rooms"
    ]

    def test_entreparticuliers_sale(self):
        query = Query()
        query.cities = []
        for city in self.backend.search_city('lille'):
            city.backend = self.backend.name
            query.cities.append(city)

        query.type = POSTS_TYPES.SALE

        self.check_against_query(query)

    def test_entreparticuliers_rent(self):
        query = Query()
        query.cities = []

        self.FIELDS_ANY_SINGLE_HOUSING = [
            "photos", "phone", "rooms"
        ]

        for city in self.backend.search_city('lille'):
            city.backend = self.backend.name
            query.cities.append(city)

        query.type = POSTS_TYPES.RENT

        self.check_against_query(query)
