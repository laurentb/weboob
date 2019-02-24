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
from .pages import YahooPage

__all__ = ['YahooBrowser']


class YahooBrowser(PagesBrowser):
    BASEURL = 'https://query.yahooapis.com'
    yahoo = URL('/v1/public/yql\?q=(?P<query>.*)&format=json', YahooPage)

    def __init__(self, unit, *args, **kwargs):
        self.unit = unit
        PagesBrowser.__init__(self, *args, **kwargs)

    def iter_city_search(self, pattern):
        query = 'select name, country, woeid, admin1 from geo.places where text="%s"' % pattern.encode('utf-8')
        return self.yahoo.go(query=query).iter_cities()

    def iter_forecast(self, city):
        query = 'select * from weather.forecast where woeid = %s and u="%s"' % (city, self.unit)
        return self.yahoo.go(query=query).iter_forecast()

    def get_current(self, city):
        query = 'select * from weather.forecast where woeid = %s and u="%s"' % (city, self.unit)
        return self.yahoo.go(query=query).get_current()
