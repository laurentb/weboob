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


from weboob.tools.browser import BasePage
from weboob.capabilities.weather import Forecast, Current, City

import datetime


__all__ = ['CityPage', 'WeatherPage', 'ForecastPage']


class CityPage(BasePage):
    def iter_city_search(self):
        for item in self.document.findall('//div[@class="searchResultsList"]/ul/li'):
            if item.attrib.get('class', '') == 'searchResultsMoreLink':
                continue
            city_name = unicode(item.text_content().strip())
            city_id = item.find('a').attrib.get("href", "").split("+")[-1]
            yield City(city_id, city_name)

class WeatherPage(BasePage):
    def get_city(self):
        parts = self.url.split('/')[-1].split('+')
        return City(parts[-1], u', '.join(parts[:-1]))

    def get_current(self):
        date = datetime.datetime.now()
        text = unicode(self.document.findall('//table[@class="twc-forecast-table twc-second"]//tr')[2].find('td').text_content().strip())
        temp = float(self.document.find('//*[@class="twc-col-1 twc-forecast-temperature"]').text_content().strip().split(u'°')[0])
        return Current(date, temp, text, u'F')

class ForecastPage(BasePage):
    def iter_forecast(self):
        trs = self.document.findall('//table[@class="twc-forecast-table twc-second"]//tr')

        for day in range (0, 10):
            text = unicode(trs[1].findall('td')[day].text_content().strip())
            try:
                tlow = float(trs[2].findall('td')[day].text_content().strip().split(u'°')[0])
            except:
                tlow = None
            try:
                thigh = float(trs[3].findall('td')[day].text_content().strip().split(u'°')[0])
            except:
                thigh = None

            date = self.document.findall('//table[@class="twc-forecast-table twc-first"]//th')[day].text
            if len (date.split(' ')) > 3:
                date = " ".join(date.split(' ', 3)[:3])
            yield Forecast(date, tlow, thigh, text, u'F')
