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


from weboob.tools.backend import Module
from weboob.capabilities.housing import CapHousing, Housing, HousingPhoto

from .browser import EntreparticuliersBrowser


__all__ = ['EntreparticuliersModule']


class EntreparticuliersModule(Module, CapHousing):
    NAME = 'entreparticuliers'
    DESCRIPTION = u'entreparticuliers.com website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    BROWSER = EntreparticuliersBrowser

    def search_city(self, pattern):
        return self.browser.search_city(pattern)

    def search_housings(self, query):
        cities = [c.id for c in query.cities if c.backend == self.name]
        if len(cities) == 0:
            return list([])

        return self.browser.search_housings(query.type, cities, query.nb_rooms,
                                            query.area_min, query.area_max,
                                            query.cost_min, query.cost_max,
                                            query.house_types)

    def get_housing(self, _id):
        return self.browser.get_housing(_id)

    def fill_housing(self, housing, fields):
        return self.browser.get_housing(housing.id, housing)

    def fill_photo(self, photo, fields):
        if 'data' in fields and photo.url and not photo.data:
            photo.data = self.browser.open(photo.url).content
        return photo

    OBJECTS = {Housing: fill_housing, HousingPhoto: fill_photo}
