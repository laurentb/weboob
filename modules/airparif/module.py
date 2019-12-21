# -*- coding: utf-8 -*-

# Copyright(C) 2019      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.tools.backend import Module
from weboob.capabilities.base import find_object
from weboob.capabilities.gauge import (
    CapGauge, SensorNotFound, Gauge, GaugeSensor,
)

from .browser import AirparifBrowser


__all__ = ['AirparifModule']


class AirparifModule(Module, CapGauge):
    NAME = 'airparif'
    DESCRIPTION = 'airparif website'
    MAINTAINER = 'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'

    BROWSER = AirparifBrowser

    def iter_gauges(self, pattern=None):
        if pattern:
            pattern = pattern.lower()

        for gauge in self.browser.iter_gauges():
            if not pattern or pattern in gauge._searching:
                yield gauge

    def _get_gauge_by_id(self, id):
        return find_object(self.browser.iter_gauges(), id=id)

    def iter_sensors(self, gauge, pattern=None):
        if pattern:
            pattern = pattern.lower()

        if not isinstance(gauge, Gauge):
            gauge = self._get_gauge_by_id(gauge)
            if gauge is None:
                raise SensorNotFound()

        if pattern is None:
            for sensor in gauge.sensors:
                yield sensor
        else:
            for sensor in gauge.sensors:
                if pattern in sensor.name.lower():
                    yield sensor

    def _get_sensor_by_id(self, id):
        gid = id.partition('.')[0]
        return find_object(self.iter_sensors(gid), id=id)

    def get_last_measure(self, sensor):
        if not isinstance(sensor, GaugeSensor):
            sensor = self._get_sensor_by_id(sensor)
        if sensor is None:
            raise SensorNotFound()
        return sensor.lastvalue
