# -*- coding: utf-8 -*-

# Copyright(C) 2010  Cedric Defortis
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.



from weboob.tools.browser import BasePage
from weboob.capabilities.weather import Forecast, Current, City

import datetime

__all__ = ['WeatherPage', 'CityPage']


class WeatherPage(BasePage):
    def get_temp_without_unit(self, temp_str):
        # It seems that the mechanize module give us some old style
        # ISO character
        return temp_str.replace(u"\xb0C", "")

    def iter_forecast(self):
        for div in self.document.getiterator('div'):
            if div.attrib.has_key("id") and div.attrib.get('id').find("jour") != -1:
                for em in div.getiterator('em'):
                    templist = em.text_content().split("/")

                    t_low = self.get_temp_without_unit(templist[0]).strip()
                    t_high = self.get_temp_without_unit(templist[1]).strip()
                    break
                for strong in div.getiterator("strong"):
                    mdate = strong.text_content()
                    break
                for img in div.getiterator("img"):
                    mtxt = img.attrib["title"]
                    break
                yield Forecast(mdate, t_low, t_high, mtxt, "C")

    def get_current(self):
        for div in self.document.getiterator('div'):
            if div.attrib.has_key("id") and div.attrib.get('id') == "blocDetails0":
                for em in div.getiterator('em'):
                    temp = self.get_temp_without_unit(em.text_content()).strip()
                    break
                for img in div.getiterator("img"):
                    mtxt = img.attrib["title"]
                    break
                mdate = str(datetime.datetime.now())
                yield Current(mdate, temp, mtxt, "C")


    def get_city(self):
        """Return the city from the forecastpage
        """
        for div in self.document.getiterator('div'):
            if div.attrib.has_key("class") and div.attrib.get("class") == "choix":
                for strong in div.getiterator("strong"):
                    city_name=strong.text +" "+ strong.tail.replace("(","").replace(")","")
                    city_id=self.url.split("/")[-1]

                    return City( city_id, city_name)


class CityPage(BasePage):
    def iter_city_search(self):
        for div in self.document.getiterator('div'):
            if div.attrib.get('id') == "column1":
                for li in div.getiterator('li'):
                    city_name = li.text_content()
                    for children in li.getchildren():
                        city_id = children.attrib.get("href").split("/")[-1]
                    mcity = City( city_id, city_name)
                    yield mcity
