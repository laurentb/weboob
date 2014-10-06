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


from weboob.deprecated.browser import Browser

from .pages import PageCity, PageConcert, PageCityList, PageDate, PageDates


__all__ = ['SueurDeMetalBrowser']


class SueurDeMetalBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'www.sueurdemetal.com'
    ENCODING = 'iso-8859-15'

    PAGES = {
        '%s://%s/ville-metal-.+.htm' % (PROTOCOL, DOMAIN): PageCity,
        r'%s://%s/detail-concert-metal.php\?c=.+' % (PROTOCOL, DOMAIN): PageConcert,
        '%s://%s/recherchemulti.php' % (PROTOCOL, DOMAIN): PageCityList,
        '%s://%s/liste-dates-concerts.php' % (PROTOCOL, DOMAIN): PageDates,
        r'%s://%s/date-metal-.+.htm' % (PROTOCOL, DOMAIN): PageDate,
    }

    def get_concerts_city(self, city):
        self.location('%s://%s/ville-metal-%s.htm' % (self.PROTOCOL, self.DOMAIN, city))
        assert self.is_on_page(PageCity)
        return self.page.get_concerts()

    def get_concerts_date(self, date_from, date_end=None):
        self.location('%s://%s/liste-dates-concerts.php' % (self.PROTOCOL, self.DOMAIN))
        assert self.is_on_page(PageDates)
        for day in self.page.get_dates_filtered(date_from, date_end):
            self.location(day['url'])
            assert self.is_on_page(PageDate)
            for data in self.page.get_concerts():
                yield data

    def get_concert(self, _id):
        self.location('%s://%s/detail-concert-metal.php?c=%s' % (self.PROTOCOL, self.DOMAIN, _id))
        assert self.is_on_page(PageConcert)
        return self.page.get_concert()

    def get_cities(self):
        self.location('%s://%s/recherchemulti.php' % (self.PROTOCOL, self.DOMAIN))
        assert self.is_on_page(PageCityList)
        return self.page.get_cities()
