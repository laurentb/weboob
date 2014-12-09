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

from weboob.browser import PagesBrowser, URL
from weboob.capabilities.housing import Query
from .pages import CityListPage, HousingListPage, HousingPage


class LeboncoinBrowser(PagesBrowser):
    BASEURL = 'http://www.leboncoin.fr'
    city = URL('ajax/location_list.html\?city=(?P<city>.*)&zipcode=(?P<zip>.*)', CityListPage)
    search = URL('(?P<type>.*)/offres/(?P<region>.*)/occasions/\?ps=(?P<ps>.*)&pe=(?P<pe>.*)&ros=(?P<ros>.*)&location=(?P<location>.*)&sqs=(?P<sqs>.*)&sqe=(?P<sqe>.*)&ret=(?P<ret>.*)&f=(?P<advert_type>.*)',
                 '(?P<_type>.*)/offres/(?P<_region>.*)/occasions.*?',
                 HousingListPage)
    housing = URL('ventes_immobilieres/(?P<_id>.*).htm', HousingPage)

    RET = {Query.HOUSE_TYPES.HOUSE: '1',
           Query.HOUSE_TYPES.APART: '2',
           Query.HOUSE_TYPES.LAND: '3',
           Query.HOUSE_TYPES.PARKING: '4',
           Query.HOUSE_TYPES.OTHER: '5'}

    def __init__(self, region, *args, **kwargs):
        super(LeboncoinBrowser, self).__init__(*args, **kwargs)
        self.region = region

    def get_cities(self, pattern):
        city = ''
        zip_code = ''
        if pattern.isdigit():
            zip_code = pattern
        else:
            city = pattern

        return self.city.go(city=city, zip=zip_code).get_cities()

    def search_housings(self, query, advert_type):
        type, cities, nb_rooms, area_min, area_max, cost_min, cost_max, ret = self.decode_query(query)
        return self.search.go(region=self.region,
                              location=cities,
                              ros=nb_rooms,
                              sqs=area_min,
                              sqe=area_max,
                              ps=cost_min,
                              pe=cost_max,
                              type=type,
                              advert_type=advert_type,
                              ret=ret).get_housing_list()

    def get_housing(self, _id, obj=None):
        return self.housing.go(_id=_id).get_housing(obj=obj)

    def decode_query(self, query):
        cities = []
        for c in query.cities:
            cities.append('%s %s' % (c.id, c.name))

        if len(cities) == 0:
            return list()

        ret = []
        for g in query.house_types:
            if g in self.RET:
                ret.append(self.RET.get(g))

        if len(ret) == 0:
            return list()

        _type = 'ventes_immobilieres'
        if query.type == Query.TYPE_RENT:
            _type = 'locations'

        self.search.go(_type=_type, _region=self.region)

        nb_rooms = '' if not query.nb_rooms else self.page.get_rooms_min(query.nb_rooms)
        area_min = '' if not query.area_min else self.page.get_area_min(query.area_min)
        area_max = '' if not query.area_max else self.page.get_area_max(query.area_max)
        cost_min = '' if not query.cost_min else self.page.get_cost_min(query.cost_min)
        cost_max = '' if not query.cost_max else self.page.get_cost_max(query.cost_max)

        return _type, ','.join(cities), nb_rooms, area_min, area_max, cost_min, cost_max, '&ret='.join(ret)
