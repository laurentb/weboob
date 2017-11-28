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
from weboob.tools.test import BackendTest
from weboob.tools.value import Value
from weboob.capabilities.housing import Query, POSTS_TYPES


class LeboncoinTest(BackendTest):
    MODULE = 'leboncoin'

    def setUp(self):
        if not self.is_backend_configured():
            self.backend.config['advert_type'] = Value(value='a')
            self.backend.config['region'] = Value(value='ile_de_france')

    def test_leboncoin(self):
        query = Query()
        query.cities = []
        query.type = POSTS_TYPES.SALE
        for city in self.backend.search_city('lille'):
            city.backend = self.backend.name
            query.cities.append(city)

        results = list(itertools.islice(self.backend.search_housings(query), 0, 20))
        self.assertTrue(len(results) > 0)
        obj = self.backend.fillobj(results[0])
        self.assertTrue(obj.url is not None, 'Missing url for "%s"' % (obj.id))
