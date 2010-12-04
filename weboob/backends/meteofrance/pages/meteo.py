# -*- coding: utf-8 -*-

# Copyright(C) 2010  Julien Veyssier
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
from weboob.capabilities.weather import ICapWeather, Forecast, Current, City

import datetime


__all__ = ['WeatherPage', 'CityResultPage']


class WeatherPage(BasePage):
    def iter_forecast(self):
        for div in self.document.getiterator('div'):
            if div.attrib.has_key("id") and div.attrib.get('id').find("jour") != -1:
                for em in div.getiterator('em'):
                    templist = em.text_content().split("/")
                    t_low = templist[0].replace(u"\xb0C", "").strip()
                    t_high = templist[1].replace(u"\xb0C", "").strip()
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
                    temp = em.text_content()
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

    def plop(self):
        for div in self.document.getiterator('div'):
            if div.attrib.get('id','') == 'column1':
                title = div.text.strip()
            elif div.attrib.get('class','') == 'download':
                url = div.getchildren()[0].attrib.get('href','')
            elif div.attrib.get('id','') == 'details':
                size = float(div.getchildren()[0].getchildren()[5].text.split('(')[1].split('Bytes')[0])
                if len(div.getchildren()) > 1 \
                        and div.getchildren()[1].attrib.get('class','') == 'col2' :
                    seed = div.getchildren()[1].getchildren()[7].text
                    leech = div.getchildren()[1].getchildren()[9].text
                else:
                    seed = div.getchildren()[0].getchildren()[24].text
                    leech = div.getchildren()[0].getchildren()[26].text
            elif div.attrib.get('class','') == 'nfo':
                description = div.getchildren()[0].text
        torrent = Torrent(id, title)
        torrent.url = url
        torrent.size = size
        torrent.seeders = int(seed)
        torrent.leechers = int(leech)
        torrent.description = description
        torrent.files = ['NYI']

        return torrent
