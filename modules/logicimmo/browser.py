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
from .pages import CitiesPage, SearchPage, HousingPage, PhonePage


class LogicimmoBrowser(PagesBrowser):
    BASEURL = 'http://www.logic-immo.com/'

    city = URL('asset/t9/t9_district/fr/(?P<size>\d*)/(?P<first_letter>\w)/(?P<pattern>.*)\.txt\?json=%22(?P<pattern2>.*)%22',
               CitiesPage)
    search = URL('(?P<type>location|vente)-immobilier-(?P<cities>.*)/options/(?P<options>.*)', SearchPage)
    housing = URL('detail-(?P<_id>.*).htm', HousingPage)
    phone = URL('(?P<urlcontact>.*)', PhonePage)

    TYPES = {Query.TYPE_RENT: 'location',
             Query.TYPE_SALE: 'vente'}

    RET = {Query.HOUSE_TYPES.HOUSE: '2',
           Query.HOUSE_TYPES.APART: '1',
           Query.HOUSE_TYPES.LAND: '3',
           Query.HOUSE_TYPES.PARKING: '10',
           Query.HOUSE_TYPES.OTHER: '14'}

    def get_cities(self, pattern):
        if pattern:
            size = len(pattern)
            first_letter = pattern[0].upper()
            return self.city.go(size=size, first_letter=first_letter, pattern=pattern.upper(),
                                pattern2=pattern.upper()).get_cities()

    def search_housings(self, type, cities, nb_rooms, area_min, area_max, cost_min, cost_max, house_types):
        options = []

        ret = []
        for house_type in house_types:
            if house_type in self.RET:
                ret.append(self.RET.get(house_type))

        if len(ret):
            options.append('groupprptypesids=%s' % ','.join(ret))

        options.append('pricemin=%s' % (cost_min if cost_min else '0'))

        if cost_max:
            options.append('pricemax=%s' % cost_max)

        options.append('areamin=%s' % (area_min if area_min else '0'))

        if area_max:
            options.append('areamax=%s' % area_max)

        if nb_rooms:
            options.append('nbrooms=%s' % nb_rooms)

        return self.search.go(type=self.TYPES.get(type, 'location'),
                              cities=cities,
                              options='/'.join(options)).iter_housings()

    def get_housing(self, _id, housing=None):
        return self.housing.go(_id=_id).get_housing(obj=housing)

    def get_phone(self, _id):
        urlcontact, params = self.housing.stay_or_go(_id=_id).get_phone_url_datas()
        return self.phone.go(urlcontact=urlcontact, params=params).get_phone()
