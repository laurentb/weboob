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

from weboob.tools.json import json

from weboob.browser import PagesBrowser, URL
from weboob.capabilities.base import empty

from .pages import CitiesPage, HousingPage, SearchPage
from .housing import RET, TYPES


class EntreparticuliersBrowser(PagesBrowser):
    BASEURL = 'https://api.entreparticuliers.com'

    cities = URL('/api/voiture/GetLocalisations/\?term=(?P<pattern>.*)', CitiesPage)
    housing = URL('/api/immo/Getannonce/\?id=(?P<_id>.*)&rubrique=(?P<_rubrique>.*)',
                  HousingPage)
    search_house = URL('/api/immo/GetBiens', SearchPage)

    def search_city(self, pattern):
        self.update_header()
        return self.cities.open(pattern=pattern).iter_cities()

    def search_housings(self, query, cities):
        self.update_header()

        data = {}
        data['rubrique'] = TYPES.get(query.type)
        data['prix_max'] = query.cost_max or None
        data['surface_min'] = query.area_min or None
        if len(cities) > 1:
            data['rayon'] = None
        else:
            data['rayon'] = 100
        data['CategorieMode'] = None
        data['CategorieMaison'] = None
        data['Kilometrage'] = None
        data['top'] = 50
        data['order_by'] = 5
        data['sort_order'] = 1
        data['lstNbPieces'] = [query.nb_rooms or 0]
        data['pageNumber'] = 1

        for city in cities:
            data['localisation'] = {}
            data['localisation']['localisationid'] = city.id
            data['localisation']['label'] = city.name
            data['localisation']['localisationType'] = 5
            data['localisationType'] = 5
            data['lstLocalisationId'] = str(city.id)

            for house_type in query.house_types:
                data['lstTbien'] = RET.get(house_type)

                for house in self.search_house.go(data=json.dumps(data)).iter_houses():
                    if (empty(query.cost_min) or house.cost >= query.cost_min) and \
                       (empty(query.area_max) or house.area <= query.area_max):
                        yield house

    def get_housing(self, _id, obj=None):
        self.reset_header()

        _id_ = _id.split('#')
        return self.housing.go(_rubrique=_id_[0], _id=_id_[1]).get_housing(obj=obj)

    def update_header(self):
        self.session.headers.update({"X-Requested-With": "XMLHttpRequest",
                                     "Content-Type": "application/json; charset=utf-8",
                                     "Accept": "application/json, text/javascript, */*; q=0.01"})

    def reset_header(self):
        self.session.headers.update({"Upgrade-Insecure-Requests": "1",
                                     "Content-Type": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                                     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
