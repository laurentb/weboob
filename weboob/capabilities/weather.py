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


from datetime import datetime, date

from weboob.tools.compat import basestring, unicode

from .base import Capability, BaseObject, Field, FloatField, \
                  StringField, UserError, NotLoaded
from .date import DateField

__all__ = ['Forecast', 'Current', 'City', 'CityNotFound', 'Temperature', 'CapWeather']


class Temperature(BaseObject):

    value =      FloatField('Temperature value')
    unit =       StringField('Input unit')

    def __init__(self, value=NotLoaded, unit = u'', url=None):
        super(Temperature, self).__init__(unicode(value), url)
        self.value = value
        if unit not in [u'C', u'F']:
            unit = u''
        self.unit = unit

    def asfahrenheit(self):
        if not self.unit:
            return u'%s' % int(round(self.value))
        elif self.unit == 'F':
            return u'%s °F' % int(round(self.value))
        else:
            return u'%s °F' % int(round((self.value * 9.0 / 5.0) + 32))

    def ascelsius(self):
        if not self.unit:
            return u'%s' % int(round(self.value))
        elif self.unit == 'C':
            return u'%s °C' % int(round(self.value))
        else:
            return u'%s °C' % int(round((self.value - 32.0) * 5.0 / 9.0))

    def __repr__(self):
        if self.value is not None and self.unit:
            return '%r %r' % (self.value, self.unit)
        return ''


class Forecast(BaseObject):
    """
    Weather forecast.
    """
    date =      Field('Date for the forecast', datetime, date, basestring)
    low =       Field('Low temperature', Temperature)
    high =      Field('High temperature', Temperature)
    text =      StringField('Comment on forecast')

    def __init__(self, date=NotLoaded, low=None, high=None, text=None, unit=None, url=None):
        super(Forecast, self).__init__(unicode(date), url)
        self.date = date
        self.low = Temperature(low, unit)
        self.high = Temperature(high, unit)
        self.text = text


class Current(BaseObject):
    """
    Current weather.
    """
    date =      DateField('Date of measure')
    text =      StringField('Comment about current weather')
    temp =      Field('Current temperature', Temperature)

    def __init__(self, date=NotLoaded, temp=None, text=None, unit=None, url=None):
        super(Current, self).__init__(unicode(date), url)
        self.date = date
        self.text = text
        self.temp = Temperature(temp, unit)


class City(BaseObject):
    """
    City where to find weather.
    """
    name =      StringField('Name of city')

    def __init__(self, id='', name=None, url=None):
        super(City, self).__init__(id, url)
        self.name = name


class CityNotFound(UserError):
    """
    Raised when a city is not found.
    """


class CapWeather(Capability):
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
