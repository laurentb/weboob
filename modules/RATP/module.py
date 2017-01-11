# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
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


from weboob.tools.backend import Module
from weboob.capabilities.gauge import CapGauge, GaugeSensor, SensorNotFound

from .browser import RATPBrowser


__all__ = ['RATPModule']


class RATPSensor(GaugeSensor):
    def __init__(self, gauge):
        super(RATPSensor, self).__init__(id="%s_sensor" % gauge.id)
        self.name = "%s status" % (gauge.name)


class RATPModule(Module, CapGauge):
    NAME = 'RATP'
    DESCRIPTION = u'RATP network status'
    MAINTAINER = u'Phyks (Lucas Verney)'
    EMAIL = 'phyks@phyks.me'
    LICENSE = 'AGPLv3+'
    VERSION = '1.3'

    BROWSER = RATPBrowser

    def get_last_measure(self, id):
        """
        Get last measures of a sensor.

        :param id: ID of the sensor.
        :type id: str
        :rtype: :class:`GaugeMeasure`
        """
        # Note: The lower the value, the higher the perturbations.
        try:
            return next(self.browser.get_status(id))
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

    def iter_sensors(self, id, pattern=None):
        """
        Iter instrument of a gauge.

        :param: ID of the gauge
        :param pattern: if specified, used to search sensors.
        :type pattern: str
        :rtype: iter[:class:`GaugeSensor`]
        """
        try:
            gauge = [
                gauge
                for gauge in self.browser.list_gauges()
                if id == gauge.id
            ][0]
            return [RATPSensor(gauge)]
        except KeyError:
            raise SensorNotFound()
