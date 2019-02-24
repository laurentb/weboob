# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Cedric Defortis
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

from weboob.browser import PagesBrowser, URL
from .pages import WeatherPage, SearchCitiesPage

__all__ = ['MeteofranceBrowser']


class MeteofranceBrowser(PagesBrowser):
    BASEURL = 'http://www.meteofrance.com'
    cities = URL('mf3-rpc-portlet/rest/lieu/facet/previsions/search/(?P<pattern>.*)', SearchCitiesPage)
    weather = URL('previsions-meteo-france/(?P<city_name>.*)/(?P<city_id>.*)', WeatherPage)

    def iter_city_search(self, pattern):
        return self.cities.go(pattern=pattern).iter_cities()

    def iter_forecast(self, city):
        return self.weather.go(city_id=city.id, city_name=city.name).iter_forecast()

    def get_current(self, city):
        return self.weather.go(city_id=city.id, city_name=city.name).get_current()
