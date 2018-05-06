# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from datetime import date, time, datetime, timedelta

from weboob.browser.elements import method, ListElement, ItemElement
from weboob.browser.filters.standard import CleanText, Field
from weboob.browser.pages import HTMLPage
from weboob.capabilities.base import FloatField, IntField, Field as BaseField
from weboob.capabilities.weather import City, Forecast, Temperature, Current
from weboob.tools.compat import quote, unicode


class DIRECTION(object):
    S = 'South'
    N = 'North'
    E = 'East'
    W = 'West'
    SE = 'South-East'
    SW = 'South-West'
    NW = 'North-West'
    NE = 'North-East'


class FullForecast(Forecast):
    wind_speed = IntField('Wind speed (in m/s)')
    wind_direction = BaseField('Wind direction', unicode)
    humidity = FloatField('Relative humidity ratio')


class FullCurrent(Current):
    wind_speed = IntField('Wind speed (in m/s)')
    wind_direction = BaseField('Wind direction', unicode)
    humidity = FloatField('Relative humidity ratio')


class CitiesPage(HTMLPage):
    ENCODING = 'utf-8'

    @method
    class iter_cities(ListElement):
        item_xpath = '//suggest'

        class item(ItemElement):
            klass = City

            obj_name = CleanText('.')

            def obj_id(self):
                return quote(Field('name')(self).encode('utf-8'))


def temp(v):
    t = Temperature()
    t.unit = 'C'
    t.value = v
    return t


class WeatherPage(HTMLPage):
    def fill_base(self, obj, n):
        obj.text = self.get_img_cell(self.titles['Temps sensible'], n)

        if 'Humidité relative moyenne' in self.titles:
            humidity = self.get_cell(self.titles['Humidité relative moyenne'], n)
        else:
            humidity = self.get_cell(self.titles['Humidité relative'], n)
        obj.humidity = float(humidity.strip('%')) / 100

        direction = self.get_cell(self.titles['Direction du vent'], n)[-2:].replace('O', 'W')
        obj.wind_direction = getattr(DIRECTION, direction)

        if 'Vitesse du vent' in self.titles:
            speed_text = self.get_cell(self.titles['Vitesse du vent'], n)
        else:
            speed_text = self.get_cell(self.titles['Vitesse moyenne du vent'], n)
        obj.wind_speed = 1000 * int(speed_text.replace('km/h', '').strip())


class HourPage(WeatherPage):
    def get_cell(self, row, col):
        return CleanText('//table[@id="meteoHour"]/tr[{row}]/td[{col}]'.format(row=row + 1, col=col + 1))(self.doc)

    def get_img_cell(self, row, col):
        return CleanText('//table[@id="meteoHour"]/tr[{row}]/td[{col}]/img/@alt'.format(row=row + 1, col=col + 1))(self.doc)

    def get_current(self):
        fore = next(iter(self.iter_forecast()))
        ret = FullCurrent()
        for f in ('date', 'text', 'wind_direction', 'wind_speed', 'humidity'):
            setattr(ret, f, getattr(fore, f))
        ret.temp = fore.high
        return ret

    def iter_forecast(self):
        d = date.today()

        self.titles = {}
        for n, tr in enumerate(self.doc.xpath('//table[@id="meteoIntit"]/tr')):
            self.titles[CleanText('.')(tr)] = n

        day_str = None
        for n in range(len(self.doc.xpath('//table[@id="meteoHour"]/tr[1]/td'))):
            obj = FullForecast()

            t = time(int(self.get_cell(self.titles['Heure'], n).rstrip('h')), 0)

            new_day_str = self.get_cell(self.titles['Jour'], n)
            if day_str is not None and day_str != new_day_str:
                d += timedelta(1)
            day_str = new_day_str
            obj.date = datetime.combine(d, t)

            obj.low = obj.high = temp(int(self.get_cell(self.titles['T° (ressentie)'], n).split('°')[0]))
            self.fill_base(obj, n)

            yield obj


class Days5Page(WeatherPage):
    def get_cell(self, row, col):
        return CleanText('//table[@id="meteo2"]/tr[2]/td[{col}]/table/tr[{row}]/td'.format(row=row + 1, col=col + 1))(self.doc)

    def get_img_cell(self, row, col):
        return CleanText('//table[@id="meteo2"]/tr[2]/td[{col}]/table/tr[{row}]/td//img/@alt'.format(row=row + 1, col=col + 1))(self.doc)

    def iter_forecast(self):
        d = date.today()

        self.titles = {}
        for n, tr in enumerate(self.doc.xpath('//table[@id="meteo2"]/tr[2]/td[1]/table/tr')):
            self.titles[CleanText('.')(tr)] = n

        for n in range(1, len(self.doc.xpath('//table[@id="meteo2"]/tr[1]/td'))):
            obj = FullForecast()
            obj.low = temp(int(self.get_cell(self.titles['Température Mini'], n).rstrip('°')))
            obj.high = temp(int(self.get_cell(self.titles['Température Maxi'], n).rstrip('°')))
            obj.date = d
            self.fill_base(obj, n)

            d += timedelta(1)
            yield obj


class Days10Page(WeatherPage):
    def get_cell(self, row, col):
        return CleanText('//table[@id="meteo2"]/tr[{row}]/td[{col}]'.format(row=row + 1, col=col + 1))(self.doc)

    def get_img_cell(self, row, col):
        return CleanText('//table[@id="meteo2"]/tr[{row}]/td[{col}]//img/@alt'.format(row=row + 1, col=col + 1))(self.doc)

    def iter_forecast(self):
        d = date.today() + timedelta(5)

        self.titles = {}
        for n, tr in enumerate(self.doc.xpath('//table[@id="meteo2"]/tr/td[1]')):
            self.titles[CleanText('.')(tr)] = n

        for n in range(1, len(self.doc.xpath('//table[@id="meteo2"]/tr[1]/td'))):
            obj = FullForecast()
            obj.low = temp(int(self.get_cell(self.titles['Température Mini'], n).rstrip('°C')))
            obj.high = temp(int(self.get_cell(self.titles['Température Maxi'], n).rstrip('°C')))
            obj.date = d
            self.fill_base(obj, n)

            d += timedelta(1)
            yield obj
