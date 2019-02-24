# -*- coding: utf-8 -*-

# Copyright(C) 2017      ZeHiro
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
from weboob.capabilities.housing import HOUSE_TYPES

from .pages import CitiesPage, SearchPage, HousingPage
from .constants import QUERY_TYPES, QUERY_HOUSE_TYPES


class AvendrealouerBrowser(PagesBrowser):
    BASEURL = 'https://www.avendrealouer.fr'

    cities = URL(r'/common/api/localities\?term=(?P<term>)', CitiesPage)
    search = URL(r'/recherche.html\?pageIndex=1&sortPropertyName=Price&sortDirection=Ascending&searchTypeID=(?P<type_id>.*)&typeGroupCategoryID=1&transactionId=1&localityIds=(?P<location_ids>.*)&typeGroupIds=(?P<type_group_ids>.*)(?P<rooms>.*)(?P<min_price>.*)(?P<max_price>.*)(?P<min_surface>.*)(?P<max_surface>.*)', SearchPage)
    search_one = URL(r'/recherche.html\?localityIds=4-36388&reference=(?P<reference>.*)&hasMoreCriterias=true&searchTypeID=1', SearchPage)
    housing = URL(r'/[vente|location].*', HousingPage)

    def get_cities(self, pattern):
        return self.cities.open(term=pattern).iter_cities()

    def search_housings(self, query):
        type_id = QUERY_TYPES[query.type]

        house_types = []
        for house_type in query.house_types:
            if house_type == HOUSE_TYPES.UNKNOWN:
                house_types = QUERY_HOUSE_TYPES[house_type]
                break
            house_types.append(QUERY_HOUSE_TYPES[house_type])

        type_group_ids = ','.join(house_types)

        location_ids = ','.join([city.id for city in query.cities])

        def build_optional_param(query_field, query_string):
            replace = ''
            if getattr(query, query_field):
                replace = '&%s=%s' % (query_string, getattr(query, query_field))
            return replace

        rooms = ''
        if query.nb_rooms:
            rooms = str(query.nb_rooms)
            for i in range(query.nb_rooms + 1, 6):
                rooms += ',%s' % str(i)
            rooms = '&roomComfortIds=%s' % rooms

        reg_exp = {
            'type_id': type_id,
            'type_group_ids': type_group_ids,
            'location_ids': location_ids,
            'rooms': rooms,
            'min_price': build_optional_param('cost_min', 'minimumPrice'),
            'max_price': build_optional_param('cost_max', 'maximumPrice'),
            'min_surface': build_optional_param('area_min', 'minimumSurface'),
            'max_surface': build_optional_param('area_max', 'maximumSurface')
        }
        return self.search.open(**reg_exp).iter_housings()

    def get_housing(self, housing_id, obj=None):
        url = self.search_one.open(reference=housing_id).get_housing_url()
        return self.open(url).page.get_housing(obj=obj)
