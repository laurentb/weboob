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
from weboob.capabilities.gauge import ICapWaterLevel
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
    VERSION = '0.b'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon'
    DESCRIPTION = 'Console application allowing to display weather and forecasts in your city.'
    CAPS = (ICapWeather, ICapWaterLevel)
    DEFAULT_FORMATTER = 'table'
    EXTRA_FORMATTERS = {'cities':    CitiesFormatter,
                        'current':   CurrentFormatter,
                        'forecasts': ForecastsFormatter,
                       }
    COMMANDS_FORMATTERS = {'cities':    'cities',
                           'current':   'current',
                           'forecasts': 'forecasts',
                          }

    def do_cities(self, pattern):
        """
        cities PATTERN

        Search cities.
        """
        self.change_path('/cities')
        for backend, city in self.do('iter_city_search', pattern, caps=ICapWeather):
            self.add_object(city)
            self.format(city)
        self.flush()

    def complete_current(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_current(self, line):
        """
        current CITY_ID

        Get current weather for specified city. Use the 'cities' command to find them.
        """
        city, = self.parse_command_args(line, 1, 1)
        _id, backend_name = self.parse_id(city)
        for backend, current in self.do('get_current', _id, backends=backend_name, caps=ICapWeather):
            if current:
                self.format(current)
        self.flush()

    def complete_forecasts(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_forecasts(self, line):
        """
        forecasts CITY_ID

        Get forecasts for specified city. Use the 'cities' command to find them.
        """
        city, = self.parse_command_args(line, 1, 1)
        _id, backend_name = self.parse_id(city)
        for backend, forecast in self.do('iter_forecast', _id, backends=backend_name, caps=ICapWeather):
            self.format(forecast)
        self.flush()

    def do_gauges(self, pattern):
        """
        rivers [PATTERN]

        List all rivers. If PATTERN is specified, search on a pattern.
        """
        self.change_path('/gauges')
        for backend, gauge in self.do('iter_gauges', pattern or None, caps=ICapWaterLevel):
            self.add_object(gauge)
            self.format(gauge)
        self.flush()

    def complete_gauge(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_gauge(self, line):
        """
        gauge GAUGE_ID

        Get history of a specific gauge (use 'rivers' to find them).
        """
        gauge, = self.parse_command_args(line, 1, 1)
        _id, backend_name = self.parse_id(gauge)
        for backend, measure in self.do('iter_gauge_history', _id, backends=backend_name, caps=ICapWaterLevel):
            self.format(measure)
        self.flush()

    def complete_last_gauge_measure(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_last_gauge_measure(self, line):
        """
        last_gauge_measure GAUGE_ID

        Get last measure of a gauge (use 'rivers' to find them).
        """
        gauge, = self.parse_command_args(line, 1, 1)
        _id, backend_name = self.parse_id(gauge)
        for backend, measure in self.do('get_last_measure', _id, backends=backend_name, caps=ICapWaterLevel):
            self.format(measure)
        self.flush()
