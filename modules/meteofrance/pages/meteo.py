
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


from weboob.tools.browser import BasePage
from weboob.capabilities.weather import Forecast, Current, City

import datetime
import re

__all__ = ['WeatherPage']


class SearchCitiesPage(BasePage):
    def iter_cities(self):
        list = self.document.getroot().xpath('//ul[@class="list-style-1"]/li/a')
        for a in list:
            m = re.search('/.*/(.*)/(\d{5})', a.attrib.get('href'))
            if m:
                mcity = City(int(m.group(2)), u'%s' % m.group(1))
                yield mcity


class WeatherPage(BasePage):
    def get_temp_without_unit(self, temp_str):
        # It seems that the mechanize module give us some old style
        # ISO character
        return float(temp_str.replace(u"\xb0C", "").strip())

    def iter_forecast(self):
        lis = self.document.getroot().xpath('//ul[@class="list-days-summary slides"]/li')
        for li in lis:
            divs = self.parser.select(li, 'div[@class="group-days-summary"]', 1, method='xpath')
            for div in divs:
                day_div = self.parser.select(div, 'div[@class="box"]', 1, method='xpath')
                date = self.parser.select(day_div, 'div[@class="box-header"]/h3', 1, method='xpath').text
                temp = self.parser.select(div, 'div/div/div[@class="day-summary-temperature"]',
                                          1, method='xpath').text_content()
                low = self.get_temp_without_unit(temp.split('|')[0])
                high = self.get_temp_without_unit(temp.split('|')[1])
                broad = self.parser.select(div, 'div/div/div[@class="day-summary-broad"]',
                                           1, method='xpath').text_content().strip()
                uvs = self.parser.select(div, 'div/div/div[@class="day-summary-uv"]',
                                         method='xpath')
                uv = u''
                if uvs is not None and len(uvs) > 0:
                    uv = u'%s' % uvs[0].text_content()
                wind = self.parser.select(div, 'div/div/div[@class="day-summary-wind"]',
                                          1, method='xpath').text_content()
                text = u'%s %s %s' % (broad, uv, wind)
                yield Forecast(date, low, high, text, u'C')

    def get_current(self):
        div = self.document.getroot().xpath('//div[@class="bloc-day-summary"]')[0]
        mdate = datetime.datetime.now()
        temp = self.parser.select(div, 'div/div/div[@class="day-summary-temperature"]',
                                  1, method='xpath').text_content()
        temperature = self.get_temp_without_unit(temp.split('|')[0])
        broad = self.parser.select(div, 'div/div/div[@class="day-summary-broad"]', 1, method='xpath').text_content()
        wind = self.parser.select(div, 'div/div/div[@class="day-summary-wind"]', 1, method='xpath').text_content()
        mtxt = u'%s %s' % (broad, wind)
        return Current(mdate, temperature, mtxt, u'C')
