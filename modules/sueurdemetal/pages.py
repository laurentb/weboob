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


from weboob.tools.browser import BasePage
from weboob.tools.date import parse_french_date
import re
from urlparse import urljoin


__all__ = ['PageCity', 'PageConcert', 'PageCityList', 'PageDate', 'PageDates']


class PageWithConcerts(BasePage):
    def extract_concert(self, concert_table):
        d = {}
        date_h3 = concert_table.iter('h3').next()
        d['date'] = parse_french_date(date_h3.text)

        cancel_h2 = next(date_h3.itersiblings('h2'), None)
        if cancel_h2 is not None and cancel_h2.text.startswith('ANNUL'):
            d['active'] = False
        else:
            d['active'] = True

        performers_table = concert_table.iterdescendants('table').next()
        d['performers'] = list(self.extract_performers(performers_table))
        d['summary'] = ' + '.join(p['name'] for p in d['performers'])
        d['description'] = d['summary']

        return d

    def extract_performers(self, performers_table):
        for performer_tr in performers_table.findall('tr'):
            performer_td = performer_tr.find('td')
            d = {'name': performer_td.find('strong').text.strip(' \t\r\n+')} # handle '+ GUESTS'
            rest = performer_td.tail
            if rest:
                d['genre'] = rest
            yield d

    def extract_id_from_url(self, url):
        return re.search(r'c=(\d+)', url).group(1)

    def extract_city_from_url(self, url):
        return re.search('metal-(.+).htm$', url).group(1)

    def extract_concert_link(self, concert_table, d):
        infos_a = concert_table.xpath('.//a[starts-with(@href, "detail-concert-metal.php")]')[0]
        infos_a = concert_table.xpath('.//a[starts-with(@href, "detail-concert-metal.php")]')[0]
        d['id'] = self.extract_id_from_url(infos_a.get('href'))
        d['url'] = 'http://www.sueurdemetal.com/detail-concert-metal.php?c=%s' % d['id']


class PageCity(PageWithConcerts):
    def get_concerts(self):
        for concert_table in self.document.xpath('//div[@id="centre-page"]//div/table'):
            yield self.extract_concert(concert_table)

    def extract_concert(self, concert_table):
        d = PageWithConcerts.extract_concert(self, concert_table)
        self.extract_concert_link(concert_table, d)
        d['city_id'] = self.extract_city_from_url(self.url)
        return d


class PageDate(PageWithConcerts):
    def get_concerts(self):
        for concert_table in self.document.xpath('//div[@id="centre-page"]//div/table'):
            yield self.extract_concert(concert_table)

    def extract_concert(self, concert_table):
        d = PageWithConcerts.extract_concert(self, concert_table)
        self.extract_concert_link(concert_table, d)
        city_a = concert_table.xpath('.//a[starts-with(@href, "ville-metal-")]')[0]
        d['city_id'] = self.extract_city_from_url(city_a.get('href'))
        return d


class PageConcert(PageWithConcerts):
    def get_concert(self):
        concert_table = self.document.xpath('//div[@id="centre-page"]//div/table')[0]
        d = self.extract_concert(concert_table)
        d['id'] = self.extract_id_from_url(self.url)
        d['url'] = self.url

        it = concert_table.iterdescendants('table')
        it.next() # ignore performers table
        infos_table = it.next()
        self.infos_table = infos_table
        info_trs = infos_table.findall('tr')
        d['room'] = (info_trs[3].findall('td')[1].text or '').strip()
        d['address'] = (info_trs[4].findall('td')[1].text or '').strip()

        price = self.parse_price(info_trs[5].findall('td')[1].text)
        if price is not None: # "None" is different from "0€"
            d['price'] = price

        city_a = self.document.xpath('//a[starts-with(@href, "ville-metal-")]')[0]
        d['city_id'] = self.extract_city_from_url(city_a.get('href'))
        d['city'] = city_a.text
        return d

    def parse_price(self, s):
        if not s:
            return
        parts = filter(None, re.split(r'[^\d.]+', s.strip()))
        if not parts:
            return
        return float(parts[-1])


class PageCityList(BasePage):
    def get_cities(self):
        cities = {}
        for option in self.document.xpath('//select[@name="ville"]/option'):
            v = option.get('value')
            if not v:
                continue
            d = {}
            d['code'], d['dept'] = re.search(r'ville-metal-(.*)-([0-9AB]+).htm$', v).groups() # french dept
            d['id'] = '%s-%s' % (d['code'], d['dept'])
            d['name'] = option.text.split('(')[0].strip()

            cities[d['name']] = d
        return cities


class PageDates(BasePage):
    def get_dates(self):
        for a in self.document.xpath('//div[@id="dateconcerts"]//a'):
            d = {}
            d['date'] = parse_french_date(a.text.strip())
            d['url'] = urljoin(self.url, a.get('href'))
            yield d

    def get_dates_filtered(self, date_from=None, date_end=None):
        for d in self.get_dates():
            date = d['date']
            if (not date_from or date_from <= date) and \
               (not date_end or date <= date_end):
                yield d
