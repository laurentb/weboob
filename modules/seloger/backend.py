# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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



from weboob.capabilities.housing import ICapHousing, City, Housing, HousingPhoto
from weboob.tools.backend import BaseBackend

from .browser import SeLogerBrowser


__all__ = ['SeLogerBackend']


class SeLogerBackend(BaseBackend, ICapHousing):
    NAME = 'seloger'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.j'
    DESCRIPTION = 'French housing website'
    LICENSE = 'AGPLv3+'
    ICON = 'http://static.poliris.com/z/portail/svx/portals/sv6_gen/favicon.png'
    BROWSER = SeLogerBrowser

    def search_housings(self, query):
        cities = [c.id for c in query.cities if c.backend == self.name]
        if len(cities) == 0:
            return list([])

        with self.browser:
            return self.browser.search_housings(query.type, cities, query.nb_rooms,
                                                query.area_min, query.area_max,
                                                query.cost_min, query.cost_max)

    def get_housing(self, housing):
        if isinstance(housing, Housing):
            id = housing.id
        else:
            id = housing
            housing = None

        with self.browser:
            return self.browser.get_housing(id, housing)

    def search_city(self, pattern):
        with self.browser:
            for categories in self.browser.search_geo(pattern):
                if categories['label'] != 'Villes':
                    continue
                for city in categories['values']:
                    if not 'value' in city:
                        continue
                    c = City(city['value'])
                    c.name = unicode(city['label'])
                    yield c

    def fill_housing(self, housing, fields):
        with self.browser:
            if fields != ['photos'] or not housing.photos:
                housing = self.browser.get_housing(housing.id)
            if 'photos' in fields:
                for photo in housing.photos:
                    if not photo.data:
                        photo.data = self.browser.readurl(photo.url)
        return housing

    def fill_photo(self, photo, fields):
        with self.browser:
            if 'data' in fields and photo.url and not photo.data:
                photo.data = self.browser.readurl(photo.url)
        return photo

    OBJECTS = {Housing: fill_housing,
               HousingPhoto: fill_photo,
              }
