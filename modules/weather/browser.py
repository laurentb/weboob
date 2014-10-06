# -*- coding: utf-8 -*-

# Copyright(C) 2012 Arno Renevier
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

from weboob.deprecated.browser import Browser

from .pages import ForecastPage, WeatherPage, CityPage

__all__ = ['WeatherBrowser']


class WeatherBrowser(Browser):
    DOMAIN = 'www.weather.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    PAGES = {}

    SEARCH_URL = 'http://www.weather.com/search/enhancedlocalsearch?where=%s'
    WEATHER_URL = 'http://www.weather.com/weather/today/%s'
    FORECAST_URL = 'http://www.weather.com/weather/tenday/%s'
    RIGHTNOW_URL = 'http://www.weather.com/weather/right-now/%s'
    USER_AGENT = Browser.USER_AGENTS['desktop_firefox']

    PAGES = {
        (SEARCH_URL.replace('.', '\\.').replace('?', '\\?') % '.*'): CityPage,
        (WEATHER_URL.replace('.', '\\.').replace('?', '\\?') % '.*'): WeatherPage,
        (FORECAST_URL.replace('.', '\\.').replace('?', '\\?') % '.*'): ForecastPage,
        (RIGHTNOW_URL.replace('.', '\\.').replace('?', '\\?') % '.*'): WeatherPage,
        }

    def iter_city_search(self, pattern):
        self.location(self.SEARCH_URL % urllib.quote_plus(pattern.encode('utf-8')))
        if self.is_on_page(CityPage):
            return self.page.iter_city_search()
        elif self.is_on_page(WeatherPage):
            return [self.page.get_city()]

    def get_current(self, city_id):
        self.location(self.WEATHER_URL % urllib.quote_plus(city_id.encode('utf-8')))
        return self.page.get_current()

    def iter_forecast(self, city_id):
        self.location(self.FORECAST_URL % urllib.quote_plus(city_id.encode('utf-8')))
        assert self.is_on_page(ForecastPage)
        return self.page.iter_forecast()
