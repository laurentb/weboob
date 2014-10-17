# -*- coding: utf-8 -*-

# Copyright(C) 2013      dud
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


from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.base import StringField
from weboob.capabilities.gauge import CapGauge, GaugeSensor, Gauge, GaugeMeasure, SensorNotFound
from weboob.tools.value import Value
from weboob.tools.ordereddict import OrderedDict

from .browser import VelibBrowser


__all__ = ['jcvelauxModule']


SENSOR_TYPES = OrderedDict(((u'available_bikes', u'Available bikes'),
                (u'available_bike_stands', u'Free stands'),
                (u'bike_stands', u'Total stands')))

CITIES = ("Paris", "Rouen", "Toulouse", "Luxembourg", "Valence", "Stockholm",
          "Goteborg", "Santander", "Amiens", "Lillestrom", "Mulhouse", "Lyon",
          "Ljubljana", "Seville", "Namur", "Nancy", "Creteil", "Bruxelles-Capitale",
          "Cergy-Pontoise", "Vilnius", "Toyama", "Kazan", "Marseille", "Nantes",
          "Besancon")


class BikeMeasure(GaugeMeasure):
    def __repr__(self):
        return '<GaugeMeasure level=%d>' % self.level


class BikeSensor(GaugeSensor):
    longitude = StringField('Longitude of the sensor')
    latitude = StringField('Latitude of the sensor')


class jcvelauxModule(Module, CapGauge):
    NAME = 'jcvelaux'
    DESCRIPTION = (u'City bike renting availability information.\nCities: %s' %
                   u', '.join(CITIES))
    MAINTAINER = u'Herve Werner'
    EMAIL = 'dud225@hotmail.com'
    VERSION = '1.1'
    LICENSE = 'AGPLv3'

    BROWSER = VelibBrowser
    STORAGE = {'boards': {}}

    CONFIG = BackendConfig(Value('city', label='City', default='Paris',
                                 choices=CITIES + ("ALL",)))

    def __init__(self, *a, **kw):
        super(jcvelauxModule, self).__init__(*a, **kw)
        self.cities = None

    def _make_gauge(self, info):
        gauge = Gauge(info['id'])
        gauge.name = unicode(info['name'])
        gauge.city = unicode(info['city'])
        gauge.object = u'bikes'
        return gauge

    def _make_sensor(self, sensor_type, info, gauge):
        id = '%s.%s' % (sensor_type, gauge.id)
        sensor = BikeSensor(id)
        sensor.gaugeid = gauge.id
        sensor.name = SENSOR_TYPES[sensor_type]
        sensor.address = unicode(info['address'])
        sensor.longitude = info['longitude']
        sensor.latitude = info['latitude']
        sensor.history = []
        return sensor

    def _make_measure(self, sensor_type, info):
        measure = BikeMeasure()
        measure.date = info['last_update']
        measure.level = float(info[sensor_type])
        return measure

    def _parse_gauge(self, info):
        gauge = self._make_gauge(info)
        gauge.sensors = []

        for type in SENSOR_TYPES:
            sensor = self._make_sensor(type, info, gauge)
            measure = self._make_measure(type, info)
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
        _, gauge_id = id.split('.', 1)
        gauge = self._get_gauge_by_id(gauge_id)
        if not gauge:
            raise SensorNotFound()
        for sensor in gauge.sensors:
            if sensor.id.lower() == id.lower():
                return sensor
