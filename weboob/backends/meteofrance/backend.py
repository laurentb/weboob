# -*- coding: utf-8 -*-

# Copyright(C) 2010  Cedric Defortis
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from weboob.capabilities.weather import ICapWeather
from weboob.tools.backend import BaseBackend

from .browser import MeteofranceBrowser


__all__ = ['MeteofranceBackend']


class MeteofranceBackend(BaseBackend, ICapWeather):
    NAME = 'meteofrance'
    MAINTAINER = 'Cedric Defortis'
    EMAIL = 'cedric@aiur.fr'
    VERSION = '0.7'
    DESCRIPTION = 'Get forecasts from the MeteoFrance website'
    LICENSE = 'GPLv3'
    BROWSER = MeteofranceBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_current(self, city_id):
        return self.browser.get_current(city_id)

    def iter_forecast(self, city_id):
        return self.browser.iter_forecast(city_id)

    def iter_city_search(self, pattern):
        return self.browser.iter_city_search(pattern)
