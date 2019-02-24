# -*- coding: utf-8 -*-

# Copyright(C) 2012 Arno Renevier
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals
from dateutil.parser import parse as parse_date

from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.pages import JsonPage
from weboob.browser.filters.standard import Format, DateTime, Env
from weboob.browser.filters.json import Dict
from weboob.capabilities.weather import Forecast, Current, City, Temperature


class CityPage(JsonPage):
    ENCODING = 'utf-8'

    @method
    class iter_cities(DictElement):
        item_xpath = '0/doc'
        ignore_duplicate = True

        class item(ItemElement):
            klass = City

            obj_id = Dict('geocode')
            obj_name = Dict('name')


class WeatherPage(JsonPage):
    @method
    class get_current(ItemElement):
        klass = Current

        obj_date = DateTime(Dict('vt1currentdatetime/dateTime'))
        obj_id = Env('city_id')
        obj_text = Format('%shPa (%s) - humidity %s%% - feels like %s°C - %s',
                          Dict('vt1observation/altimeter'),
                          Dict('vt1observation/barometerTrend'),
                          Dict('vt1observation/humidity'),
                          Dict('vt1observation/feelsLike'),
                          Dict('vt1observation/phrase'))

        def obj_temp(self):
            temp = Dict('vt1observation/temperature')(self)
            return Temperature(float(temp), 'C')

    def iter_forecast(self):
        forecast = self.doc['vt1dailyForecast']
        for i in range(1, len(forecast['dayOfWeek'])):
            date = parse_date(forecast['validDate'][1])
            tlow = float(forecast['day']['temperature'][i])
            thigh = tlow
            text = forecast['day']['narrative'][i]
            yield Forecast(date, tlow, thigh, text, 'C')
