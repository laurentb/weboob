# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
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

from __future__ import unicode_literals


from weboob.browser import PagesBrowser, URL

from .constants import QUERY_TYPES
from .pages import CitiesPage, HousingPage, SearchPage, SearchResultsPage


class FonciaBrowser(PagesBrowser):
    BASEURL = 'https://fr.foncia.com'

    cities = URL(r'/recherche/autocomplete\?term=(?P<term>.+)', CitiesPage)
    housing = URL(r'/(?P<type>[^/]+)/.*\d+.htm', HousingPage)
    search_results = URL(r'/(?P<type>[^/]+)/.*', SearchResultsPage)
    search = URL(r'/(?P<type>.+)', SearchPage)

    def get_cities(self, pattern):
        """
        Get cities matching a given pattern.
        """
        return self.cities.open(term=pattern).iter_cities()

    def search_housings(self, query, cities):
        """
        Search for housings matching given query.
        """
        try:
            query_type = QUERY_TYPES[query.type]
        except KeyError:
            return []

        self.search.go(type=query_type).do_search(query, cities)
        return self.page.iter_housings(query_type=query.type)

    def get_housing(self, housing):
        """
        Get specific housing.
        """
        query_type, housing = housing.split(':')
        self.search.go(type=query_type).find_housing(query_type, housing)
        return self.page.get_housing()
