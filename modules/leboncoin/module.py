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


from weboob.tools.backend import Module
from weboob.capabilities.housing import (CapHousing, Housing, HousingPhoto)
from .browser import LeboncoinBrowser


__all__ = ['LeboncoinModule']


class LeboncoinModule(Module, CapHousing):
    NAME = 'leboncoin'
    DESCRIPTION = u'search house on leboncoin website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = LeboncoinBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_housing(self, _id):
        return self.browser.get_housing(_id)

    def fill_housing(self, housing, fields):
        if 'phone' in fields:
            housing.phone = self.browser.get_phone(housing.id)
            fields.remove('phone')

        if len(fields) > 0:
            self.browser.get_housing(housing.id, housing)

        return housing

    def fill_photo(self, photo, fields):
        if 'data' in fields and photo.url and not photo.data:
            photo.data = self.browser.open(photo.url).content
        return photo

    def search_city(self, pattern):
        return self.browser.get_cities(pattern)

    def search_housings(self, query):
        return self.browser.search_housings(query, self.name)

    OBJECTS = {Housing: fill_housing, HousingPhoto: fill_photo}
