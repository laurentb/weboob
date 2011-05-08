# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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

from datetime import datetime

from weboob.capabilities.weather import ICapWeather
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['WetBoobs']

class ForecastsFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'low', 'high', 'unit')

    def flush(self):
        pass

    def format_dict(self, item):
        result = u'%s* %-15s%s (%s°%s - %s°%s)' % (self.BOLD, '%s:' % item['date'], self.NC, item['low'], item['unit'], item['high'], item['unit'])
        if 'text' in item and item['text']:
            result += ' %s' % item['text']
        return result

class CurrentFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'temp')

    def flush(self):
        pass

    def format_dict(self, item):
        if isinstance(item['date'], datetime):
            date = item['date'].strftime('%y-%m-%d %H:%M:%S')
        else:
            date = item['date']

        result = u'%s%s%s: %s' % (self.BOLD, date, self.NC, item['temp'])
        if 'unit' in item and item['unit']:
            result += u'°%s' % item['unit']
        if 'text' in item and item['text']:
            result += u' - %s' % item['text']
        return result

class CitiesFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'name')
    count = 0

    def flush(self):
        self.count = 0

    def format_dict(self, item):
        self.count += 1
        if self.interactive:
            backend = item['id'].split('@', 1)[1]
            result = u'%s* (%d) %s (%s)%s' % (self.BOLD, self.count, item['name'], backend, self.NC)
        else:
            result = u'%s* (%s) %s%s' % (self.BOLD, item['id'], item['name'], self.NC)
        return result

class WetBoobs(ReplApplication):
    APPNAME = 'wetboobs'
    VERSION = '0.9'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon'
    DESCRIPTION = 'Console application allowing to display weather and forecasts in your city.'
    CAPS = ICapWeather
    EXTRA_FORMATTERS = {'cities':    CitiesFormatter,
                        'current':   CurrentFormatter,
                        'forecasts': ForecastsFormatter,
                       }
    COMMANDS_FORMATTERS = {'search':    'cities',
                           'current':   'current',
                           'forecasts': 'forecasts',
                          }

    cities = []

    def do_search(self, pattern):
        """
        search PATTERN

        Search cities.
        """
        self.cities = []
        for backend, city in self.do('iter_city_search', pattern):
            self.format(city)
            self.cities.append(city)
        self.flush()

    def parse_id(self, id):
        if self.interactive:
            try:
                city = self.cities[int(id) - 1]
            except (IndexError,ValueError):
                pass
            else:
                id = '%s@%s' % (city.id, city.backend)
        return ReplApplication.parse_id(self, id)

    def _complete_id(self):
        return ['%s@%s' % (city.id, city.backend) for city in self.cities]

    def complete_current(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_id()

    def do_current(self, line):
        """
        current CITY_ID

        Get current weather for specified city. Use the 'search' command to find
        its ID.
        """
        city, = self.parse_command_args(line, 1, 1)
        _id, backend_name = self.parse_id(city)
        for backend, current in self.do('get_current', _id, backends=backend_name):
            if current:
                self.format(current)
        self.flush()

    def complete_forecasts(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_id()

    def do_forecasts(self, line):
        """
        forecasts CITY_ID

        Get forecasts for specified city. Use the 'search' command to find
        its ID.
        """
        city, = self.parse_command_args(line, 1, 1)
        _id, backend_name = self.parse_id(city)
        for backend, forecast in self.do('iter_forecast', _id, backends=backend_name):
            self.format(forecast)
        self.flush()
