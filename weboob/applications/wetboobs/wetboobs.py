# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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


import sys

from weboob.core import CallErrors
from weboob.capabilities.weather import ICapWeather, CityNotFound
from weboob.tools.application.repl import ReplApplication


__all__ = ['WetBoobs']


class WetBoobs(ReplApplication):
    APPNAME = 'wetboobs'
    VERSION = '0.4'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    CAPS = ICapWeather

    def do_search(self, pattern):
        """
        search PATTERN

        Search cities.
        """
        for backend, city in self.do('iter_city_search', pattern):
            self.format(city)
        self.flush()

    def do_current(self, city):
        """
        current CITY

        Get current weather.
        """
        for backend, current in self.do('get_current', city):
            self.format(current)
        self.flush()

    def do_forecasts(self, city):
        """
        forecasts CITY

        Get forecasts.
        """
        for backend, forecast in self.do('iter_forecast', city):
            self.format(forecast)
        self.flush()
