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


import logging

from weboob.core import CallErrors
from weboob.capabilities.weather import ICapWeather, CityNotFound
from weboob.tools.application.console import ConsoleApplication


__all__ = ['WetBoobs']


class WetBoobs(ConsoleApplication):
    APPNAME = 'wetboobs'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'

    def main(self, argv):
        self.load_backends(ICapWeather)

        return self.process_command(*argv[1:])

    @ConsoleApplication.command('search cities')
    def command_search(self, pattern):
        for backend, city in self.do('iter_city_search', pattern):
            self.format(city, backend.name)

    @ConsoleApplication.command('get current weather')
    def command_current(self, city):
        try:
            for backend, current in self.do('get_current', city):
                self.format(current, backend.name)
        except CallErrors, e:
            for error in e:
                if isinstance(error, CityNotFound):
                    logging.error('City "%s" not found' % city)
                else:
                    raise error

    @ConsoleApplication.command('get forecasts')
    def command_forecasts(self, city):
        try:
            for backend, forecast in self.do('iter_forecast', city):
                self.format(forecast, backend.name)
        except CallErrors, e:
            for error in e:
                if isinstance(error, CityNotFound):
                    logging.error('City "%s" not found' % city)
                else:
                    raise error
