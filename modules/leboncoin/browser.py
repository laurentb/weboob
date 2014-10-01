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

from weboob.tools.browser2 import PagesBrowser, URL

from .pages import CityListPage, HousingListPage, HousingPage


class LeboncoinBrowser(PagesBrowser):
    BASEURL = 'http://www.leboncoin.fr'
    city = URL('ajax/location_list.html\?city=(?P<city>.*)&zipcode=(?P<zip>.*)', CityListPage)
    search = URL('(?P<type>.*)/offres/ile_de_france/occasions/\?ps=(?P<ps>.*)&pe=(?P<pe>.*)&ros=(?P<ros>.*)&location=(?P<location>.*)&sqs=(?P<sqs>.*)&sqe=(?P<sqe>.*)&ret=(?P<ret>.*)&f=(?P<advert_type>.*)',
                 '(ventes_immobilieres|locations)/offres/ile_de_france/occasions/\?.*',
                 HousingListPage)
    housing = URL('ventes_immobilieres/(?P<_id>.*).htm', HousingPage)

    def get_cities(self, pattern):
        city = ''
        zip_code = ''
        if pattern.isdigit():
            zip_code = pattern
        else:
            city = pattern

        return self.city.go(city=city, zip=zip_code).get_cities()

    def search_housings(self, type, cities, nb_rooms, area_min, area_max, cost_min, cost_max, ret, advert_type):
        return self.search.go(location=cities,
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
