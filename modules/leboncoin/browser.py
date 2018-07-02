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

from weboob.tools.json import json

from weboob.browser import PagesBrowser, URL
from weboob.capabilities.housing import (TypeNotSupported, POSTS_TYPES,
                                         HOUSE_TYPES, ADVERT_TYPES)
from .pages import CityListPage, HousingListPage, HousingPage, PhonePage, HomePage


class LeboncoinBrowser(PagesBrowser):
    BASEURL = 'https://www.leboncoin.fr/'
    city = URL('ajax/location_list.html\?city=(?P<city>.*)&zipcode=(?P<zip>.*)', CityListPage)
    housing = URL('ventes_immobilieres/(?P<_id>.*).htm', HousingPage)

    home = URL('annonces/offres/', HomePage)
    api = URL('https://api.leboncoin.fr/finder/search', HousingListPage)
    phone = URL('https://api.leboncoin.fr/api/utils/phonenumber.json', PhonePage)

    TYPES = {POSTS_TYPES.RENT: '10',
             POSTS_TYPES.FURNISHED_RENT: '10',
             POSTS_TYPES.SALE: '9',
             POSTS_TYPES.SHARING: '11', }

    RET = {HOUSE_TYPES.HOUSE: '1',
           HOUSE_TYPES.APART: '2',
           HOUSE_TYPES.LAND: '3',
           HOUSE_TYPES.PARKING: '4',
           HOUSE_TYPES.OTHER: '5'}

    def __init__(self, *args, **kwargs):
        super(LeboncoinBrowser, self).__init__(*args, **kwargs)

    def get_cities(self, pattern):
        city = ''
        zip_code = ''
        if pattern.isdigit():
            zip_code = pattern
        else:
            city = pattern.replace(" ", "_")

        return self.city.go(city=city, zip=zip_code).get_cities()

    def search_housings(self, query, module_name):

        if query.type not in self.TYPES.keys():
            return TypeNotSupported()

        data = {}
        data['filters'] = {}
        data['filters']['category'] = {}
        data['filters']['category']['id'] = self.TYPES.get(query.type)
        data['filters']['enums'] = {}
        data['filters']['enums']['ad_type'] = ['offer']

        data['filters']['enums']['real_estate_type'] = []
        for t in query.house_types:
            t = self.RET.get(t)
            if t:
                data['filters']['enums']['real_estate_type'].append(t)

        if query.type == POSTS_TYPES.FURNISHED_RENT:
            data['filters']['enums']['furnished'] = ['1']
        elif query.type == POSTS_TYPES.RENT:
            data['filters']['enums']['furnished'] = ['2']

        data['filters']['keywords'] = {}
        data['filters']['ranges'] = {}

        if query.cost_max or query.cost_min:
            data['filters']['ranges']['price'] = {}

            if query.cost_max:
                data['filters']['ranges']['price']['max'] = query.cost_max

                if query.cost_min:
                    data['filters']['ranges']['price']['min'] = query.cost_min

        if query.area_max or query.area_min:
            data['filters']['ranges']['square'] = {}
            if query.area_max:
                data['filters']['ranges']['square']['max'] = query.area_max

            if query.area_min:
                data['filters']['ranges']['square']['min'] = query.area_min

        if query.nb_rooms:
            data['filters']['ranges']['rooms'] = {}
            data['filters']['ranges']['rooms']['min'] = query.nb_rooms

        data['filters']['location'] = {}
        data['filters']['location']['city_zipcodes'] = []

        for c in query.cities:
            if c.backend == module_name:
                _c = c.id.split(' ')
                __c = {}
                __c['city'] = _c[0]
                __c['zipcode'] = _c[1]
                __c['label'] = c.name

                data['filters']['location']['city_zipcodes'].append(__c)

        if len(query.advert_types) == 1:
            if query.advert_types[0] == ADVERT_TYPES.PERSONAL:
                data['owner_type'] = 'private'
            elif query.advert_types[0] == ADVERT_TYPES.PROFESSIONAL:
                data['owner_type'] = 'pro'
        else:
            data['owner_type'] = 'all'

        data['limit'] = 100
        data['limit_alu'] = 3
        data['offset'] = 0

        self.session.headers.update({"api_key": self.home.go().get_api_key()})
        return self.api.go(data=json.dumps(data)).get_housing_list(query_type=query.type, data=data)

    def get_housing(self, _id, obj=None):
        return self.housing.go(_id=_id).get_housing(obj=obj)

    def get_phone(self, _id):
        api_key = self.housing.stay_or_go(_id=_id).get_api_key()
        data = {'list_id': _id,
                'app_id': 'leboncoin_web_utils',
                'key': api_key,
                'text': 1, }
        return self.phone.go(data=data).get_phone()
