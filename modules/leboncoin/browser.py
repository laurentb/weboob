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
from weboob.capabilities.housing import Query, TypeNotSupported
from .pages import CityListPage, HousingListPage, HousingPage, PhonePage


class LeboncoinBrowser(PagesBrowser):
    BASEURL = 'https://www.leboncoin.fr/'
    city = URL('ajax/location_list.html\?city=(?P<city>.*)&zipcode=(?P<zip>.*)', CityListPage)
    search = URL('(?P<type>.*)/offres/(?P<region>.*)/occasions/\?(?P<_ps>ps|mrs)=(?P<ps>.*)&(?P<_pe>pe|mre)=(?P<pe>.*)&ros=(?P<ros>.*)&location=(?P<location>.*)&sqs=(?P<sqs>.*)&sqe=(?P<sqe>.*)&ret=(?P<ret>.*)&f=(?P<advert_type>.*)',
                 '(?P<_type>.*)/offres/(?P<_region>.*)/occasions.*?',
                 HousingListPage)
    housing = URL('ventes_immobilieres/(?P<_id>.*).htm', HousingPage)
    phone = URL('https://api.leboncoin.fr/api/utils/phonenumber.json', PhonePage)

    TYPES = {Query.TYPE_RENT: 'locations',
             Query.TYPE_SALE: 'ventes_immobilieres',
             Query.TYPE_SHARING: 'colocations', }

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

    def search_housings(self, query, advert_type, module_name):
        if query.type not in self.TYPES:
            return TypeNotSupported()

        type, cities, nb_rooms, area_min, area_max, cost_min, cost_max, ret = self.decode_query(query, module_name)
        if len(cities) == 0 or len(ret) == 0:
            return list()

        return self.search.go(region=self.region,
                              location=cities,
                              ros=nb_rooms,
                              sqs=area_min,
                              sqe=area_max,
                              _ps="mrs" if query.type == Query.TYPE_RENT else "ps",
                              ps=cost_min,
                              _pe="mre" if query.type == Query.TYPE_RENT else "pe",
                              pe=cost_max,
                              type=type,
                              advert_type=advert_type,
                              ret=ret).get_housing_list()

    def get_housing(self, _id, obj=None):
        housing = self.housing.go(_id=_id).get_housing(obj=obj)
        housing.phone = self.get_phone(_id)
        return housing

    def get_phone(self, _id):
        api_key = self.housing.stay_or_go(_id=_id).get_api_key()
        data = {'list_id': _id,
                'app_id': 'leboncoin_web_utils',
                'key': api_key,
                'text': 1, }
        return self.phone.go(data=data).get_phone()

    def decode_query(self, query, module_name):
        cities = [c.name for c in query.cities if c.backend == module_name]
        ret = [self.RET.get(g) for g in query.house_types if g in self.RET]
        _type = self.TYPES.get(query.type)

        self.search.go(_type=_type, _region=self.region)

        nb_rooms = '' if not query.nb_rooms else self.page.get_rooms_min(query.nb_rooms)
        area_min = '' if not query.area_min else self.page.get_area_min(query.area_min)
        area_max = '' if not query.area_max else self.page.get_area_max(query.area_max)
        cost_min = '' if not query.cost_min else self.page.get_cost_min(query.cost_min, query.type)
        cost_max = '' if not query.cost_max else self.page.get_cost_max(query.cost_max, query.type)

        return _type, ','.join(cities), nb_rooms, area_min, area_max, cost_min, cost_max, '&ret='.join(ret)
