# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from __future__ import with_statement

import urllib2
from xml.dom import minidom

# TODO store datetime objects instead of strings
# from datetime import datetime

from weboob.capabilities.weather import ICapWeather, CityNotFound, Current, Forecast, City
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import BaseBrowser


__all__ = ['YahooBackend']


class YahooBackend(BaseBackend, ICapWeather):
    NAME = 'yahoo'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.7.1'
    DESCRIPTION = 'Yahoo'
    LICENSE = 'GPLv3'
    BROWSER = BaseBrowser
    WEATHER_URL = 'http://weather.yahooapis.com/forecastrss?w=%s&u=%s'
    SEARCH_URL = 'http://fr.meteo.yahoo.com/search/weather?p=%s'

    def create_default_browser(self):
        return self.create_browser()

    def iter_city_search(self, pattern):
        # minidom doesn't seem to work with that page

        #handler = urllib2.urlopen((self.SEARCH_URL % pattern).replace(' ','+'))
        #dom = minidom.parse(handler)
        #handler.close()
        #results = dom.getElementById('search-results')
        #for no in results.childNodes:
        #    print no.nodeValue

        # so i use a basic but efficient parsing
        with self.browser:
            content = self.browser.readurl((self.SEARCH_URL % pattern.encode('utf-8')).replace(' ','+'))

        page=''
        for line in content.split('\n'):
            if "<title>" in line and "Prévisions et Temps" in line:
                page="direct"
            elif "<title>" in line and "Résultats de la recherche" in line:
                page="resultats"

            if page == "resultats":
                if '/redirwoei/' in line:
                    cities = line.split('/redirwoei/')
                    for c in cities:
                        if "strong" in c:
                            cid = c.split("'")[0]
                            cname = c.split("'")[1].replace("><strong>","").replace("</strong>","").split("</a>")[0]
                            yield City(cid, cname.decode('utf-8'))
            elif page == "direct":
                if 'div id="yw-breadcrumb"' in line:
                    l = line.split('</a>')
                    region = l[2].split('>')[-1]
                    country = l[1].split('>')[-1]
                    city = l[3].split('</li>')[1].replace('<li>','')
                    cid = line.split("/?unit")[0].split('-')[-1]
                    yield City(cid, (city+", "+region+", "+country).decode('utf-8'))

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
        return Current(current.getAttribute('date'), int(current.getAttribute('temp')), current.getAttribute('text'), 'C')

    def iter_forecast(self, city_id):
        dom = self._get_weather_dom(city_id)
        for forecast in dom.getElementsByTagName('yweather:forecast'):
            yield Forecast(forecast.getAttribute('date'),
                           int(forecast.getAttribute('low')),
                           int(forecast.getAttribute('high')),
                           forecast.getAttribute('text'),
                           'C',
                           )
