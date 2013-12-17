# -*- coding: utf-8 -*-

# Copyright(C) 2013  Florent Fourcot
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


from weboob.capabilities.gauge import ICapGauge, SensorNotFound
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter

import sys

__all__ = ['Boobsize']


class Boobsize(ReplApplication):
    APPNAME = 'Boosize'
    VERSION = '0.h'
    COPYRIGHT = 'Copyright(C) 2013 Florent Fourcot'
    DESCRIPTION = "Console application allowing to display various sensors and gauges values."
    SHORT_DESCRIPTION = "display sensors and gauges values"
    CAPS = (ICapGauge)
    DEFAULT_FORMATTER = 'table'

    def main(self, argv):
        self.load_config()
        return ReplApplication.main(self, argv)

    def bcall_error_handler(self, backend, error, backtrace):
        if isinstance(error, SensorNotFound):
            msg = unicode(error) or 'Sensor not found (hint: try sensors command)'
            print >>sys.stderr, 'Error(%s): %s' % (backend.name, msg)
        else:
            return ReplApplication.bcall_error_handler(self, backend, error, backtrace)

    def do_search(self, pattern):
        """
        search [PATTERN]

        Display all gauges. If PATTERN is specified, search on a pattern.
        """
        self.change_path([u'gauges'])
        self.start_format()
        for backend, gauge in self.do('iter_gauges', pattern or None, caps=ICapGauge):
            self.cached_format(gauge)

    def complete_search(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_details(self, line):
        """
        details GAUGE_ID

        Display details of all sensors of the gauge.
        """
        gauge, pattern = self.parse_command_args(line, 2, 1)
        _id, backend_name = self.parse_id(gauge)

        self.start_format()
        for backend, sensor in self.do('iter_sensors', _id, pattern=pattern, backends=backend_name, caps=ICapGauge):
            self.format(sensor)

    def do_history(self, line):
        """
        history SENSOR_ID

        Get history of a specific sensor (use 'search' to find a gauge, and sensors GAUGE_ID to list sensors attached to the gauge).
        """
        gauge, = self.parse_command_args(line, 1, 1)
        _id, backend_name = self.parse_id(gauge)

        self.start_format()
        for backend, measure in self.do('iter_gauge_history', _id, backends=backend_name, caps=ICapGauge):
            self.format(measure)

    def complete_last_sensor_measure(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_last_sensor_measure(self, line):
        """
        last_sensor_measure SENSOR_ID

        Get last measure of a sensor.
        """
        gauge, = self.parse_command_args(line, 1, 1)
        _id, backend_name = self.parse_id(gauge)

        self.start_format()
        for backend, measure in self.do('get_last_measure', _id, backends=backend_name, caps=ICapGauge):
            self.format(measure)
