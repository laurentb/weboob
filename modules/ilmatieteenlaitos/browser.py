# -*- coding: utf-8 -*-

# Copyright(C) 2015 Matthieu Weber
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

from weboob.browser.browsers import PagesBrowser
from weboob.browser.url import URL
from .pages import WeatherPage, SearchCitiesPage, ObservationsPage

__all__ = ['IlmatieteenlaitosBrowser']


class IlmatieteenlaitosBrowser(PagesBrowser):
    BASEURL = 'http://ilmatieteenlaitos.fi'
    cities = URL('/etusivu\?p_p_id=locationmenuportlet_WAR_fmiwwwweatherportlets&p_p_lifecycle=2&p_p_state=normal&'
                 'p_p_mode=view&p_p_cacheability=cacheLevelFull&term=(?P<pattern>.*)', SearchCitiesPage)
    weather_query = URL('/paikallissaa\?p_p_id=locationmenuportlet_WAR_fmiwwwweatherportlets&p_p_lifecycle=1&'
                        'p_p_state=normal&p_p_mode=view&_locationmenuportlet_WAR_fmiwwwweatherportlets_action='
                        'changelocation')
    weather = URL('/saa/(?P<city_url>.*)', WeatherPage)
    observations = URL('/observation-data\?station=(?P<station_id>.*)', ObservationsPage)

    def iter_city_search(self, pattern):
        return self.cities.go(pattern=pattern).iter_cities()

    def iter_forecast(self, city):
        return self.weather_query.go(data={"place": city.name, "forecast": "short"}).iter_forecast()

    def get_current(self, city):
        station_id = self.weather_query.go(data={"place": city.name, "forecast": "short"}).get_station_id()
        return self.observations.go(station_id=station_id).get_current()
