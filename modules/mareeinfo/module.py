# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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
from weboob.capabilities.gauge import CapGauge, Gauge, SensorNotFound
from .browser import MareeinfoBrowser


__all__ = ['MareeinfoModule']


class MareeinfoModule(Module, CapGauge):
    NAME = 'mareeinfo'
    DESCRIPTION = u'Un module qui permet d\' aller a la pêche aux moules totalement informé'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = MareeinfoBrowser

    def get_last_measure(self, sensor_id):
        gauge_id = sensor_id.split('-')[0]
        return find_object(self.iter_sensors(gauge_id), id=sensor_id, error=SensorNotFound).lastvalue

    def iter_gauge_history(self, sensor_id):
        gauge_id = sensor_id.split('-')[0]
        return find_object(self.iter_sensors(gauge_id), id=sensor_id, error=SensorNotFound).history

    def iter_gauges(self, pattern=None):
        for _gauge in self.browser.get_harbor_list(pattern):
            if pattern is not None:
                gauge = self.browser.get_harbor_infos(_gauge)
                yield gauge
            else:
                yield _gauge

    def iter_sensors(self, gauge, pattern=None):
        if not isinstance(gauge, Gauge):
            gauge = find_object(self.iter_gauges(), id=gauge, error=SensorNotFound)

        gauge = self.browser.get_harbor_infos(gauge)
        if pattern is None:
            for sensor in gauge.sensors:
                yield sensor
        else:
            lowpattern = pattern.lower()
            for sensor in gauge.sensors:
                if lowpattern in sensor.name.lower():
                    yield sensor
