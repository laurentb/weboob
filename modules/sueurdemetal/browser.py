# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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

from __future__ import unicode_literals

from weboob.browser import PagesBrowser, URL

from .pages import PageCity, PageConcert, PageCityList, PageDate, PageDates


__all__ = ['SueurDeMetalBrowser']


class SueurDeMetalBrowser(PagesBrowser):
    BASEURL = 'http://www.sueurdemetal.com'

    city = URL(r'/ville-metal-(?P<city>.+).htm', PageCity)
    concert = URL(r'/detail-concert-metal.php\?c=(?P<id>.+)', PageConcert)
    cities = URL(r'/recherchemulti.php', PageCityList)
    dates = URL(r'/liste-dates-concerts.php', PageDates)
    date = URL(r'/date-metal-.+.htm', PageDate)

    def get_concerts_city(self, city):
        self.city.go(city=city)
        assert self.city.is_here()
        return self.page.get_concerts()

    def get_concerts_date(self, date_from, date_end=None):
        self.dates.go()
        assert self.dates.is_here()
        for day in self.page.get_dates_filtered(date_from, date_end):
            self.location(day['url'])
            assert self.date.is_here()
            for data in self.page.get_concerts():
                yield data

    def get_concert(self, _id):
        self.concert.go(id=_id)
        assert self.concert.is_here()
        return self.page.get_concert()

    def get_cities(self):
        self.cities.go()
        assert self.cities.is_here()
        return self.page.get_cities()
