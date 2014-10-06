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


from weboob.deprecated.browser import Page
from weboob.capabilities.weather import Forecast, Current, City

import datetime


class CityPage(Page):
    def iter_city_search(self):
        for item in self.document.findall('//div[@class="searchResultsList"]/ul/li'):
            if item.attrib.get('class', '') == 'searchResultsMoreLink':
                continue
            city_name = unicode(item.text_content().strip())
            city_id = item.find('a').attrib.get("href", "").split("+")[-1]
            yield City(city_id, city_name)


class WeatherPage(Page):
    def get_city(self):
        parts = self.url.split('/')[-1].split('+')
        return City(parts[-1], u', '.join(parts[:-1]))

    def get_current(self):
        date = datetime.datetime.now()
        text = unicode(self.document.findall('//p[@class="wx-narrative"]')[0].text_content().strip())
        temp = float(self.document.find('//p[@class="wx-temp"]').text_content().strip().split(u'°')[0])
        return Current(date, temp, text, u'F')


class ForecastPage(Page):
    def iter_forecast(self):
        divs = self.document.findall('//div[@class="wx-daypart"]')

        for day in range (0, len(divs)):
            div = divs[day].find('div[@class="wx-conditions"]')
            text = unicode(div.find('p[@class="wx-phrase"]').text_content().strip())
            try:
                thigh = float(div.find('p[@class="wx-temp"]').text_content().strip().split(u'°')[0])
            except:
                thigh = None
            try:
                tlow = float(div.find('p[@class="wx-temp-alt"]').text_content().strip().split(u'°')[0])
            except:
                tlow = None
            date = divs[day].find('h3/span').text_content().strip()
            #date = self.document.findall('//table[@class="twc-forecast-table twc-first"]//th')[day].text
            #if len (date.split(' ')) > 3:
            #    date = " ".join(date.split(' ', 3)[:3])
            yield Forecast(date, tlow, thigh, text, u'F')
