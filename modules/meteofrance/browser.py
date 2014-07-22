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
from .pages.meteo import WeatherPage, SearchCitiesPage
from weboob.capabilities.weather import CityNotFound

__all__ = ['MeteofranceBrowser']


class MeteofranceBrowser(BaseBrowser):
    DOMAIN = 'www.meteofrance.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    WEATHER_URL = '{0}://{1}/previsions-meteo-france/{{city_name}}/{{city_id}}'.format(PROTOCOL, DOMAIN)
    CITY_SEARCH_URL = 'http://www.meteofrance.com/recherche/resultats'
    PAGES = {
        WEATHER_URL.format(city_id=".*", city_name=".*"): WeatherPage,
        CITY_SEARCH_URL: SearchCitiesPage,
        }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def iter_city_search(self, pattern):
        datas = {'facet': 'previsions',
                 'search-type': 'previsions',
                 'query': pattern}
        self.location(self.CITY_SEARCH_URL, data=urllib.urlencode(datas))
        assert self.is_on_page(SearchCitiesPage)
        return self.page.iter_cities()

    def iter_forecast(self, city_id):
        mcity = self.get_city(city_id)
        self.location(self.WEATHER_URL.format(city_id=mcity.id, city_name=mcity.name))
        assert self.is_on_page(WeatherPage)
        return self.page.iter_forecast()

    def get_current(self, city_id):
        mcity = self.get_city(city_id)
        self.location(self.WEATHER_URL.format(city_id=mcity.id, city_name=mcity.name))
        assert self.is_on_page(WeatherPage)
        return self.page.get_current()

    def get_city(self, city_id):
        cities = self.iter_city_search(city_id)
        for city in cities:
            if city_id == city.id:
                return city
        raise CityNotFound('Unable to find a city whose id is %s' % city_id)
