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


from weboob.capabilities.weather import ICapWeather
from weboob.capabilities.gauge import ICapWaterLevel
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter


__all__ = ['WetBoobs']

class ForecastsFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'low', 'high')

    temperature_display = staticmethod(lambda t: u'%s' % t.value)

    def format_obj(self, obj, alias):
        result = u'%s* %-15s%s (%s - %s)' % (self.BOLD, '%s:' % obj.date, self.NC, self.temperature_display(obj.low), self.temperature_display(obj.high))
        if hasattr(obj, 'text') and obj.text:
            result += ' %s' % obj.text
        return result

class CurrentFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'temp')

    temperature_display = staticmethod(lambda t: u'%s' % t.value)

    def format_obj(self, obj, alias):
        result = u'%s%s%s: %s' % (self.BOLD, obj.date, self.NC, self.temperature_display(obj.temp))
        if hasattr(obj, 'text') and obj.text:
            result += u' - %s' % obj.text
        return result

class CitiesFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'name')

    def get_title(self, obj):
        return obj.name


class WetBoobs(ReplApplication):
    APPNAME = 'wetboobs'
    VERSION = '0.e'
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

    def main(self, argv):
        self.load_config()
        return ReplApplication.main(self, argv)

    def do_cities(self, pattern):
        """
        cities PATTERN

        Search cities.
        """
        self.change_path(['cities'])
        self.start_format()
        for backend, city in self.do('iter_city_search', pattern, caps=ICapWeather):
            self.cached_format(city)
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

        tr = self.config.get('settings', 'temperature_display', default='C')
        if tr == 'C':
            self.formatter.temperature_display = lambda t: t.ascelsius()
        elif tr == 'F':
            self.formatter.temperature_display = lambda t: t.asfahrenheit()

        self.start_format()
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

        tr = self.config.get('settings', 'temperature_display', default='C')
        if tr == 'C':
            self.formatter.temperature_display = lambda t: t.ascelsius()
        elif tr == 'F':
            self.formatter.temperature_display = lambda t: t.asfahrenheit()
        self.start_format()

        for backend, forecast in self.do('iter_forecast', _id, backends=backend_name, caps=ICapWeather):
            self.format(forecast)
        self.flush()

    def do_gauges(self, pattern):
        """
        gauges [PATTERN]

        List all rivers. If PATTERN is specified, search on a pattern.
        """
        self.change_path([u'gauges'])
        self.start_format()
        for backend, gauge in self.do('iter_gauges', pattern or None, caps=ICapWaterLevel):
            self.cached_format(gauge)
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

        self.start_format()
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

        self.start_format()
        for backend, measure in self.do('get_last_measure', _id, backends=backend_name, caps=ICapWaterLevel):
            self.format(measure)
        self.flush()
