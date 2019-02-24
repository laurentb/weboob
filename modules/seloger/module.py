# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


from weboob.capabilities.housing import CapHousing, Housing, HousingPhoto
from weboob.tools.backend import Module

from .browser import SeLogerBrowser


__all__ = ['SeLogerModule']


class SeLogerModule(Module, CapHousing):
    NAME = 'seloger'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
    DESCRIPTION = 'French housing website'
    LICENSE = 'AGPLv3+'
    ICON = 'http://static.poliris.com/z/portail/svx/portals/sv6_gen/favicon.png'
    BROWSER = SeLogerBrowser

    def search_housings(self, query):
        cities = [c.id for c in query.cities if c.backend == self.name]
        if len(cities) == 0:
            return list([])

        return self.browser.search_housings(query.type, cities, query.nb_rooms,
                                            query.area_min, query.area_max,
                                            query.cost_min, query.cost_max,
                                            query.house_types,
                                            query.advert_types)

    def get_housing(self, housing):
        if isinstance(housing, Housing):
            id = housing.id
        else:
            id = housing
            housing = None

        return self.browser.get_housing(id, housing)

    def search_city(self, pattern):
        return self.browser.search_geo(pattern)

    def fill_photo(self, photo, fields):
        if 'data' in fields and photo.url and not photo.data:
            photo.data = self.browser.open(photo.url).content
        return photo

    def fill_housing(self, housing, fields):
        return self.browser.get_housing(housing.id, housing)

    OBJECTS = {HousingPhoto: fill_photo, Housing: fill_housing}
