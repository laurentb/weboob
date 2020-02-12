# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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
from weboob.capabilities.weather import CapWeather

from .browser import LameteoagricoleBrowser


__all__ = ['LameteoagricoleModule']


class LameteoagricoleModule(Module, CapWeather):
    NAME = 'lameteoagricole'
    DESCRIPTION = u'lameteoagricole website'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'

    BROWSER = LameteoagricoleBrowser

    def iter_city_search(self, pattern):
        return self.browser.iter_cities(pattern)

    def get_current(self, city_id):
        return self.browser.get_current(city_id)

    def iter_forecast(self, city_id):
        return self.browser.iter_forecast(city_id)
