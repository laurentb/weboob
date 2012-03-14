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


__all__ = ['WeatherPage', 'CityPage']


class WeatherPage(BasePage):
    def get_temp_without_unit(self, temp_str):
        # It seems that the mechanize module give us some old style
        # ISO character
        return int(temp_str.replace(u"\xb0C", "").strip())

    def iter_forecast(self):
        for div in self.document.getiterator('li'):
            if div.attrib.get('class', '').startswith('jour'):
                mdate = div.xpath('./dl/dt')[0].text
                t_low = self.get_temp_without_unit(div.xpath('.//dd[@class="minmax"]/strong')[0].text)
                t_high = self.get_temp_without_unit(div.xpath('.//dd[@class="minmax"]/strong')[1].text)
                mtxt = div.xpath('.//dd')[0].text
                yield Forecast(mdate, t_low, t_high, mtxt, 'C')
            elif div.attrib.get('class', '').startswith('lijourle'):
                for em in div.getiterator('em'):
                    templist = em.text_content().split("/")

                    t_low = self.get_temp_without_unit(templist[0])
                    t_high = self.get_temp_without_unit(templist[1])
                    break
                for strong in div.getiterator("strong"):
                    mdate = strong.text_content()
                    break
                for img in div.getiterator("img"):
                    mtxt = img.attrib["title"]
                    break
                yield Forecast(mdate, t_low, t_high, mtxt, "C")

    def get_current(self):
        div = self.document.getroot().xpath('//div[@class="bloc_details"]/ul/li/dl')[0]
        mdate = datetime.datetime.now()
        temp = self.get_temp_without_unit(div.xpath('./dd[@class="minmax"]')[0].text)
        mtxt = div.find('dd').find('img').attrib['title']
        return Current(mdate, temp, mtxt, 'C')

    def get_city(self):
        """
        Return the city from the forecastpage.
        """
        for div in self.document.getiterator('div'):
            if div.attrib.get("class", "") == "choix":
                for strong in div.getiterator("strong"):
                    city_name = strong.text + " " + strong.tail.replace("(", "").replace(")", "")
                    city_id = self.url.split("/")[-1]
                    return City(city_id, city_name)


class CityPage(BasePage):
    def iter_city_search(self):
        for div in self.document.getiterator('div'):
            if div.attrib.get('id') == "column1":
                for li in div.getiterator('li'):
                    city_name = li.text_content()
                    for children in li.getchildren():
                        city_id = children.attrib.get("href").split("/")[-1]
                    mcity = City(city_id, city_name)
                    yield mcity
