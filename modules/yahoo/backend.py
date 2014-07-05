# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon
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

import urllib2
from xml.dom import minidom
from dateutil.parser import parse as parse_dt


from weboob.capabilities.weather import CapWeather, CityNotFound, Current, Forecast, City
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import StandardBrowser


__all__ = ['YahooBackend']


class YahooBackend(BaseBackend, CapWeather):
    NAME = 'yahoo'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.j'
    DESCRIPTION = 'Yahoo!'
    LICENSE = 'AGPLv3+'
    BROWSER = StandardBrowser
    WEATHER_URL = 'http://weather.yahooapis.com/forecastrss?w=%s&u=%s'

    def create_default_browser(self):
        return self.create_browser(parser='json')

    def iter_city_search(self, pattern):
        args = {'q':  'select line1, line2, line3, line4, city, uzip, statecode, countrycode, latitude, longitude, '
                      'country, woeid, quality, house, street, state from locdrop.placefinder '
                      'where text="%s" and locale="fr-FR" and gflags="f"' % pattern.encode('utf-8'),
                      'format': 'json',
                }
        doc = self.browser.location(self.browser.buildurl('http://locdrop.query.yahoo.com/v1/public/yql', **args))

        cities = doc['query']['results']['Result']
        if not isinstance(cities, (tuple, list)):
            cities = [cities]

        for result in cities:
            c = City(result['woeid'], u'%s, %s, %s' % (result['city'], result['state'], result['country']))
            yield c

    def _get_weather_dom(self, city_id):
        handler = urllib2.urlopen(self.WEATHER_URL % (city_id, 'c'))
        dom = minidom.parse(handler)
        handler.close()
        if not dom.getElementsByTagName('yweather:condition'):
            raise CityNotFound('City not found: %s' % city_id)

        return dom

    def get_current(self, city_id):
        dom = self._get_weather_dom(city_id)
        current = dom.getElementsByTagName('yweather:condition')[0]
        return Current(parse_dt(current.getAttribute('date')).date(),
                       float(current.getAttribute('temp')), unicode(current.getAttribute('text')), u'C')

    def iter_forecast(self, city_id):
        dom = self._get_weather_dom(city_id)
        for forecast in dom.getElementsByTagName('yweather:forecast'):
            yield Forecast(parse_dt(forecast.getAttribute('date')).date(),
                           float(forecast.getAttribute('low')),
                           float(forecast.getAttribute('high')),
                           unicode(forecast.getAttribute('text')),
                           u'C',
                           )
