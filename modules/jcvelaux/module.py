# -*- coding: utf-8 -*-

# Copyright(C) 2013      dud
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

from __future__ import unicode_literals

from collections import OrderedDict

from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.base import UserError
from weboob.capabilities.gauge import CapGauge, GaugeSensor, Gauge, GaugeMeasure, SensorNotFound
from weboob.tools.value import Value, ValueBackendPassword

from .browser import VelibBrowser


__all__ = ['jcvelauxModule']


SENSOR_TYPES = OrderedDict([('available_bikes', 'Available bikes'),
                            ('available_bike_stands', 'Free stands'),
                            ('bike_stands', 'Total stands')])

CITIES = ("Rouen", "Toulouse", "Luxembourg", "Valence", "Stockholm",
          "Goteborg", "Santander", "Amiens", "Lillestrom", "Mulhouse", "Lyon",
          "Ljubljana", "Seville", "Namur", "Nancy", "Creteil", "Bruxelles-Capitale",
          "Cergy-Pontoise", "Vilnius", "Toyama", "Kazan", "Marseille", "Nantes",
          "Besancon")


class BikeMeasure(GaugeMeasure):
    def __repr__(self):
        return '<GaugeMeasure level=%d>' % self.level


class jcvelauxModule(Module, CapGauge):
    NAME = 'jcvelaux'
    DESCRIPTION = ('City bike renting availability information.\nCities: %s' %
                   ', '.join(CITIES))
    MAINTAINER = 'Herve Werner'
    EMAIL = 'dud225@hotmail.com'
    VERSION = '2.1'
    LICENSE = 'AGPLv3'

    BROWSER = VelibBrowser

    CONFIG = BackendConfig(Value('city', label='City', default='Lyon',
                                 choices=CITIES + ("ALL",)),
                           ValueBackendPassword('api_key', label='Optional API key',
                                                default='', noprompt=True))

    def __init__(self, *a, **kw):
        super(jcvelauxModule, self).__init__(*a, **kw)
        self.cities = None

    def create_default_browser(self):
        api_key = self.config['api_key'].get()
        return self.create_browser(api_key)

    def _make_gauge(self, info):
        gauge = Gauge(info['id'])
        gauge.name = info['name']
        gauge.city = info['city']
        gauge.object = 'bikes'
        return gauge

    def _make_sensor(self, sensor_type, info, gauge):
        id = '%s.%s' % (sensor_type, gauge.id)
        sensor = GaugeSensor(id)
        sensor.gaugeid = gauge.id
        sensor.name = SENSOR_TYPES[sensor_type]
        sensor.address = '%s' % info['address']
        sensor.longitude = info['longitude']
        sensor.latitude = info['latitude']
        sensor.history = []
        return sensor

    def _make_measure(self, sensor_type, info, gauge):
        id = '%s.%s' % (sensor_type, gauge.id)

        measure = BikeMeasure(id)
        measure.date = info['last_update']
        measure.level = float(info[sensor_type])
        return measure

    def _parse_gauge(self, info):
        gauge = self._make_gauge(info)
        gauge.sensors = []

        for type in SENSOR_TYPES:
            sensor = self._make_sensor(type, info, gauge)
            measure = self._make_measure(type, info, gauge)
            sensor.lastvalue = measure
            gauge.sensors.append(sensor)

        return gauge

    def _contract(self):
        contract = self.config.get('city').get()
        if contract.lower() == 'all':
            contract = None
        return contract

    def iter_gauges(self, pattern=None):
        if pattern is None:
            for jgauge in self.browser.get_station_list(contract=self._contract()):
                yield self._parse_gauge(jgauge)
        else:
            lowpattern = pattern.lower()
            for jgauge in self.browser.get_station_list(contract=self._contract()):
                gauge = self._parse_gauge(jgauge)
                if lowpattern in gauge.name.lower() or lowpattern in gauge.city.lower():
                    yield gauge

    def iter_sensors(self, gauge, pattern=None):
        if not isinstance(gauge, Gauge):
            gauge = self._get_gauge_by_id(gauge)
            if gauge is None:
                raise SensorNotFound()

        if pattern is None:
            for sensor in gauge.sensors:
                yield sensor
        else:
            lowpattern = pattern.lower()
            for sensor in gauge.sensors:
                if lowpattern in sensor.name.lower():
                    yield sensor

    def get_last_measure(self, sensor):
        if not isinstance(sensor, GaugeSensor):
            sensor = self._get_sensor_by_id(sensor)
        if sensor is None:
            raise SensorNotFound()
        return sensor.lastvalue

    def _fetch_cities(self):
        if self.cities:
            return

        self.cities = {}
        jcontract = self.browser.get_contracts_list()
        for jcontract in jcontract:
            for city in jcontract['cities']:
                self.cities[city.lower()] = jcontract['name']

    def _get_gauge_by_id(self, id):
        jgauge = self.browser.get_station_infos(id)
        if jgauge:
            return self._parse_gauge(jgauge)
        else:
            return None

    def _get_sensor_by_id(self, id):
        try:
            sensor_name, gauge_name, contract = id.split('.')
        except ValueError:
            raise UserError('Expected format NAME.ID.CITY for sensor: %r' % id)

        gauge = self._get_gauge_by_id('%s.%s' % (gauge_name, contract))
        if not gauge:
            raise SensorNotFound()
        for sensor in gauge.sensors:
            if sensor.id.lower() == id.lower():
                return sensor
