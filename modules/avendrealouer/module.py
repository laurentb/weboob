# -*- coding: utf-8 -*-

# Copyright(C) 2017      ZeHiro
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

from __future__ import unicode_literals


from weboob.tools.backend import Module
from weboob.capabilities.housing import CapHousing, Housing

from .browser import AvendrealouerBrowser


__all__ = ['AvendrealouerModule']


class AvendrealouerModule(Module, CapHousing):
    NAME = u'avendrealouer'
    DESCRIPTION = 'avendrealouer website'
    MAINTAINER = 'ZeHiro'
    EMAIL = 'public@abossy.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'

    BROWSER = AvendrealouerBrowser

    def get_housing(self, housing):
        """
        Get an housing from an ID.

        :param housing: ID of the housing
        :type housing: str
        :rtype: :class:`Housing` or None if not found.
        """
        return self.browser.get_housing(housing)

    def search_city(self, pattern):
        """
        Search a city from a pattern.

        :param pattern: pattern to search
        :type pattern: str
        :rtype: iter[:class:`City`]
        """
        return self.browser.get_cities(pattern)

    def search_housings(self, query):
        """
        Search housings.

        :param query: search query
        :type query: :class:`Query`
        :rtype: iter[:class:`Housing`]
        """
        return self.browser.search_housings(query)

    def fill_housing(self, housing, fields):
        if 'photos' in fields and housing.photos:
            for photo in housing.photos:
                photo.data = self.browser.open(photo.url)
        return housing

    OBJECTS = {Housing: fill_housing}
