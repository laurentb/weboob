# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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

from .base import IBaseCap, CapBaseObject


__all__ = ['City', 'CityNotFound', 'Current', 'Forecast', 'ICapWeather']


class Forecast(CapBaseObject):
    def __init__(self, date, low, high, text, unit):
        CapBaseObject.__init__(self, date)
        self.add_field('date', (basestring,datetime), date)
        self.add_field('low', (int,float), low)
        self.add_field('high', (int,float), high)
        self.add_field('text', basestring, text)
        self.add_field('unit', basestring, unit)

class Current(CapBaseObject):
    def __init__(self, date, temp, text, unit):
        CapBaseObject.__init__(self, date)
        self.add_field('date', (basestring,datetime), date)
        self.add_field('text', basestring, text)
        self.add_field('temp', (int,float), temp)
        self.add_field('unit', basestring, unit)

class City(CapBaseObject):
    def __init__(self, id, name):
        CapBaseObject.__init__(self, id)
        self.add_field('name', basestring, name)

class CityNotFound(Exception):
    pass

class ICapWeather(IBaseCap):
    def iter_city_search(self, pattern):
        raise NotImplementedError()

    def get_current(self, city_id):
        raise NotImplementedError()

    def iter_forecast(self, city_id):
        raise NotImplementedError()
