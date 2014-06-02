# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Cedric Defortis
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


import urllib

from weboob.tools.browser import BaseBrowser
from weboob.tools.json import json as simplejson
from weboob.capabilities.weather import City

from .pages.meteo import WeatherPage
import re

__all__ = ['MeteofranceBrowser']


class MeteofranceBrowser(BaseBrowser):
    DOMAIN = 'www.meteofrance.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    WEATHER_URL = '{0}://{1}/previsions-meteo-france/{{city_name}}/{{city_id}}'.format(PROTOCOL, DOMAIN)
    CITY_SEARCH_URL = '{0}://{1}/mf3-rpc-portlet/rest/lieu/facet/previsions/search/{{city_pattern}}'\
                      .format(PROTOCOL, DOMAIN)
    PAGES = {
        WEATHER_URL.format(city_id=".*", city_name=".*"): WeatherPage,
        }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def iter_city_search(self, pattern):
        searchurl = self.CITY_SEARCH_URL.format(city_pattern=urllib.quote_plus(pattern.encode('utf-8')))
        response = self.openurl(searchurl)
        return self.parse_cities_result(response)

    def parse_cities_result(self, datas):
        cities = simplejson.loads(datas.read(), self.ENCODING)
        re_id = re.compile('\d{5}', re.DOTALL)
        for city in cities:
            if re_id.match(city['codePostal']):
                mcity = City(int(city['codePostal']), u'%s' % city['slug'])
                yield mcity

    def iter_forecast(self, city_id):
        mcity = self.iter_city_search(city_id).next()
        self.location(self.WEATHER_URL.format(city_id=mcity.id, city_name=mcity.name))
        assert self.is_on_page(WeatherPage)

        return self.page.iter_forecast()

    def get_current(self, city_id):
        mcity = self.iter_city_search(city_id).next()
        self.location(self.WEATHER_URL.format(city_id=mcity.id, city_name=mcity.name))
        assert self.is_on_page(WeatherPage)
        return self.page.get_current()
