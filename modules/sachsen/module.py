# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Florent Fourcot
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

from .browser import SachsenBrowser
from weboob.capabilities.gauge import CapGauge, GaugeSensor, Gauge,\
        SensorNotFound
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module


__all__ = ['SachsenLevelModule']


class SachsenLevelModule(Module, CapGauge):
    NAME = 'sachsen'
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u"Level of Sachsen river"
    BROWSER = SachsenBrowser

    def iter_gauges(self, pattern=None):
        if pattern is None:
            for gauge in self.browser.get_rivers_list():
                yield gauge
        else:
            lowpattern = pattern.lower()
            for gauge in self.browser.get_rivers_list():
                if lowpattern in gauge.name.lower()\
                        or lowpattern in gauge.object.lower():
                    yield gauge

    def _get_sensor_by_id(self, id):
        for gauge in self.browser.get_rivers_list():
            for sensor in gauge.sensors:
                if id == sensor.id:
                    return sensor
        raise SensorNotFound()

    def iter_sensors(self, gauge, pattern=None):
        if not isinstance(gauge, Gauge):
            gauge = find_object(self.browser.get_rivers_list(), id=gauge, error=SensorNotFound)
        if pattern is None:
            for sensor in gauge.sensors:
                yield sensor
        else:
            lowpattern = pattern.lower()
            for sensor in gauge.sensors:
                if lowpattern in sensor.name.lower():
                    yield sensor

    def iter_gauge_history(self, sensor):
        if not isinstance(sensor, GaugeSensor):
            sensor = self._get_sensor_by_id(sensor)
        return self.browser.iter_history(sensor)

    def get_last_measure(self, sensor):
        if not isinstance(sensor, GaugeSensor):
            sensor = self._get_sensor_by_id(sensor)
        return sensor.lastvalue
