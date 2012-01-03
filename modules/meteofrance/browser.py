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

from .pages.meteo import WeatherPage, CityPage


__all__ = ['MeteofranceBrowser']


class MeteofranceBrowser(BaseBrowser):
    DOMAIN = 'france.meteofrance.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    WEATHER_URL = '{0}://{1}/france/meteo?PREVISIONS_PORTLET.path=previsionsville/{{cityid}}'.format(PROTOCOL, DOMAIN)
    CITY_SEARCH_URL = '{0}://{1}/france/accueil/resultat?RECHERCHE_RESULTAT_PORTLET.path=rechercheresultat&' \
        'query={{city_pattern}}&type=PREV_FRANCE&satellite=france'.format(PROTOCOL, DOMAIN)
    PAGES = {
        WEATHER_URL.format(cityid=".*"): WeatherPage,
        CITY_SEARCH_URL.format(city_pattern=".*"): CityPage,
        'http://france.meteofrance.com/france/accueil/resultat.*': CityPage,
        'http://france.meteofrance.com/france/meteo.*': WeatherPage,
        }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def iter_city_search(self, pattern):
        searchurl = self.CITY_SEARCH_URL.format(city_pattern=urllib.quote_plus(pattern.encode('utf-8')))
        self.location(searchurl)

        if self.is_on_page(CityPage):
            # Case 1: there are multiple results for the pattern:
            return self.page.iter_city_search()
        else:
            # Case 2: there is only one result, and the website send directly
            # the browser on the forecast page:
            return [self.page.get_city()]

    def iter_forecast(self, city_id):
        self.location(self.WEATHER_URL.format(cityid=city_id))

        assert self.is_on_page(WeatherPage)
        return self.page.iter_forecast()

    def get_current(self, city_id):
        self.location(self.WEATHER_URL.format(cityid=city_id))

        assert self.is_on_page(WeatherPage)
        return self.page.get_current()
