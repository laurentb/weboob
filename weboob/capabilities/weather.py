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

from .base import IBaseCap, CapBaseObject, Field, DateField, FloatField, StringField


__all__ = ['Forecast', 'Current', 'City', 'CityNotFound', 'ICapWeather']


class Forecast(CapBaseObject):
    """
    Weather forecast.
    """
    date =      Field('Date for the forecast', datetime, basestring)
    low =       FloatField('Low temperature')
    high =      FloatField('High temperature')
    text =      StringField('Comment on forecast')
    unit =      StringField('Unit used for temperatures')

    def __init__(self, date, low, high, text, unit):
        CapBaseObject.__init__(self, unicode(date))
        self.date = date
        self.low = low
        self.high = high
        self.text = text
        self.unit = unit

class Current(CapBaseObject):
    """
    Current weather.
    """
    date =      DateField('Date of measure')
    text =      StringField('Comment about current weather')
    temp =      FloatField('Current temperature')
    unit =      StringField('Unit used for temperature')

    def __init__(self, date, temp, text, unit):
        CapBaseObject.__init__(self, unicode(date))
        self.date = date
        self.text = text
        self.temp = temp
        self.unit = unit

class City(CapBaseObject):
    """
    City where to find weather.
    """
    name =      StringField('Name of city')

    def __init__(self, id, name):
        CapBaseObject.__init__(self, id)
        self.name = name

class CityNotFound(Exception):
    """
    Raised when a city is not found.
    """

class ICapWeather(IBaseCap):
    """
    Capability for weather websites.
    """
    def iter_city_search(self, pattern):
        """
        Look for a city.

        :param pattern: pattern to search
        :type pattern: str
        :rtype: iter[:class:`City`]
        """
        raise NotImplementedError()

    def get_current(self, city_id):
        """
        Get current weather.

        :param city_id: ID of the city
        :rtype: :class:`Current`
        """
        raise NotImplementedError()

    def iter_forecast(self, city_id):
        """
        Iter forecasts of a city.

        :param city_id: ID of the city
        :rtype: iter[:class:`Forecast`]
        """
        raise NotImplementedError()
