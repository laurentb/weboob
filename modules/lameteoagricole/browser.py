# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals


from weboob.browser import PagesBrowser, URL

from .pages import CitiesPage, HourPage, Days5Page, Days10Page


class LameteoagricoleBrowser(PagesBrowser):
    BASEURL = 'https://www.lameteoagricole.net'

    cities = URL(r'/autocomplete/autocomplete_ajax.php\?table=meteo_communes&field=NomComMaj&search=(?P<pattern>.*)', CitiesPage)
    hour = URL(r'/meteo-heure-par-heure/(?P<code>[^.]+).html',
               r'/index_meteo-heure-par-heure.php\?communehome=(?P<id>.*)',
               HourPage)
    day5 = URL(r'/previsions-meteo-agricole/(?P<code>[^.]+).html',
               r'/index.php\?communehome=(?P<id>.*)',
               Days5Page)
    day10 = URL(r'/meteo-a-10-jours/(?P<code>[^.]+).html',
                r'/index_meteo-a-10-jours.php\?communehome=(?P<id>.*)',
                Days10Page)

    def iter_cities(self, pattern):
        self.cities.go(pattern=pattern)
        return self.page.iter_cities()

    def get_current(self, id):
        self.hour.go(id=id)
        assert self.hour.is_here()
        return self.page.get_current()

    def iter_forecast(self, id):
        self.hour.go(id=id)
        for f in self.page.iter_forecast():
            yield f

        self.day5.go(id=id)
        for f in self.page.iter_forecast():
            yield f

        self.day10.go(id=id)
        for f in self.page.iter_forecast():
            yield f
