# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon
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

from collections import OrderedDict

from weboob.capabilities.weather import CapWeather
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value

from .browser import YahooBrowser


__all__ = ['YahooModule']


class YahooModule(Module, CapWeather):
    NAME = 'yahoo'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.6'
    DESCRIPTION = 'Yahoo! Weather.'
    LICENSE = 'AGPLv3+'
    BROWSER = YahooBrowser

    units_choice = OrderedDict([('c', 'International System of Units'),
                                ('f', 'U.S. System of Units')])

    CONFIG = BackendConfig(Value('units', label=u'System of Units', choices=units_choice))

    def create_default_browser(self):
        return self.create_browser(unit=self.config['units'].get())

    def iter_city_search(self, pattern):
        return self.browser.iter_city_search(pattern)

    def get_current(self, city_id):
        return self.browser.get_current(city_id)

    def iter_forecast(self, city_id):
        return self.browser.iter_forecast(city_id)
