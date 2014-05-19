# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Cedric Defortis
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


from weboob.capabilities.weather import ICapWeather
from weboob.tools.backend import BaseBackend

from .browser import MeteofranceBrowser


__all__ = ['MeteofranceBackend']


class MeteofranceBackend(BaseBackend, ICapWeather):
    NAME = 'meteofrance'
    MAINTAINER = u'Cedric Defortis'
    EMAIL = 'cedric@aiur.fr'
    VERSION = '0.j'
    DESCRIPTION = 'Get forecasts from the MeteoFrance website'
    LICENSE = 'AGPLv3+'
    BROWSER = MeteofranceBrowser

    def get_current(self, city_id):
        return self.browser.get_current(city_id)

    def iter_forecast(self, city_id):
        return self.browser.iter_forecast(city_id)

    def iter_city_search(self, pattern):
        return self.browser.iter_city_search(pattern)
