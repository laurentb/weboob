# -*- coding: utf-8 -*-

# Copyright(C) 2015      Bezleputh
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


from weboob.tools.backend import Module
from weboob.capabilities.housing import (CapHousing, HousingPhoto,
                                         ADVERT_TYPES, Housing)

from .browser import EntreparticuliersBrowser


__all__ = ['EntreparticuliersModule']


class EntreparticuliersModule(Module, CapHousing):
    NAME = 'entreparticuliers'
    DESCRIPTION = u'entreparticuliers.com website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '2.1'

    BROWSER = EntreparticuliersBrowser

    def search_city(self, pattern):
        return self.browser.search_city(pattern)

    def search_housings(self, query):
        if(len(query.advert_types) == 1 and
           query.advert_types[0] == ADVERT_TYPES.PROFESSIONAL):
            # Entreparticuliers is personal only
            return list()

        cities = [c for c in query.cities if c.backend == self.name]
        if len(cities) == 0:
            return []

        return self.browser.search_housings(query, cities)

    def get_housing(self, _id):
        return self.browser.get_housing(_id)

    def fill_photo(self, photo, fields):
        if 'data' in fields and photo.url and not photo.data:
            photo.data = self.browser.open(photo.url).content
        return photo

    def fill_housing(self, housing, fields):
        if len(fields) > 0:
            self.browser.get_housing(housing.id, housing)

        return housing

    OBJECTS = {HousingPhoto: fill_photo, Housing: fill_housing}
