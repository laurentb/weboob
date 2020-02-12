# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
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


from weboob.tools.backend import Module
from weboob.capabilities.base import find_object
from weboob.capabilities.gauge import CapGauge, GaugeSensor, SensorNotFound, Gauge

from .browser import RATPBrowser


__all__ = ['RATPModule']


class RATPSensor(GaugeSensor):
    def __init__(self, gauge):
        super(RATPSensor, self).__init__(id="%s_sensor" % gauge.id)
        self.name = "%s status" % (gauge.name)


class RATPModule(Module, CapGauge):
    NAME = 'ratp'
    DESCRIPTION = u'RATP network status'
    MAINTAINER = u'Phyks (Lucas Verney)'
    EMAIL = 'phyks@phyks.me'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'

    BROWSER = RATPBrowser

    def get_last_measure(self, sensor):
        """
        Get last measures of a sensor.

        :param sensor: ID of the sensor.
        :type sensor: str
        :rtype: :class:`GaugeMeasure`
        """
        # Note: The lower the value, the higher the perturbations.
        try:
            return next(self.browser.get_status(sensor))
        except KeyError:
            return SensorNotFound()

    def iter_gauges(self, pattern=None):
        """
        Iter gauges.

        :param pattern: if specified, used to search gauges.
        :type pattern: str
        :rtype: iter[:class:`Gauge`]
        """
        if not pattern:
            return self.browser.list_gauges()
        else:
            return [
                gauge
                for gauge in self.browser.list_gauges()
                if pattern in gauge.name
            ]

    def iter_sensors(self, gauge, pattern=None):
        """
        Iter instrument of a gauge.

        :param: ID of the gauge
        :param pattern: if specified, used to search sensors.
        :type pattern: str
        :rtype: iter[:class:`GaugeSensor`]
        """
        if not isinstance(gauge, Gauge):
            gauge = find_object(self.iter_gauges(), id=gauge, error=SensorNotFound)
        sensor = RATPSensor(gauge)
        sensor.lastvalue = self.get_last_measure(sensor.id)
        return [sensor]
