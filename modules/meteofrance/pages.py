
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

from datetime import date

from weboob.browser.pages import JsonPage, HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.capabilities.weather import Forecast, Current, City, Temperature
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import CleanHTML
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Format


class DictElement(ListElement):
    def find_elements(self):
        if self.item_xpath is not None:
            for el in self.el:
                yield el
        else:
            yield self.el


class SearchCitiesPage(JsonPage):
    @method
    class iter_cities(DictElement):
        item_xpath = '.'
        ignore_duplicate = True

        class item(ItemElement):
            klass = City

            def condition(self):
                return Dict('type')(self) == "VILLE_FRANCE"

            obj_id = Dict('codePostal')
            obj_name = Dict('slug')


class WeatherPage(HTMLPage):
    @method
    class iter_forecast(ListElement):
        item_xpath = '//div[@class="group-days-summary"]/div'

        class item(ItemElement):
            klass = Forecast

            obj_id = CleanText('./div/div/h3[@class="day-summary-title"]')
            obj_date = CleanText('./div/div/h3[@class="day-summary-title"]')

            def obj_low(self):
                temp = CleanDecimal(Regexp(CleanText('./div/div/div[@class="day-summary-temperature"]'),
                                           '(.*)\|.*'))(self)
                unit = Regexp(CleanText('./div/div/div[@class="day-summary-temperature"]'), u'.*\xb0(\w) \|.*')(self)
                return Temperature(float(temp), unit)

            def obj_high(self):
                temp = CleanDecimal(Regexp(CleanText('./div/div/div[@class="day-summary-temperature"]'),
                                           '.*\|(.*)'))(self)
                unit = Regexp(CleanText('./div/div/div[@class="day-summary-temperature"]'), u'.*\|.*\xb0(\w).*')(self)
                return Temperature(float(temp), unit)

            obj_text = Format('%s %s %s %s', CleanHTML('./div/div/div[@class="day-summary-broad"]'),
                              CleanHTML('./div/div/div[@class="day-summary-wind"]'),
                              CleanHTML('./div/div/div[@class="day-summary-uv"]'),
                              CleanHTML('./div/div/div[@class="day-summary-indice"]/img/@title'))

    @method
    class get_current(ItemElement):
        klass = Current

        obj_id = date.today()
        obj_date = date.today()
        obj_text = Format('%s %s %s %s',
                          CleanHTML('(//div[@class="group-days-summary"])[1]/div[1]/div/div/div[@class="day-summary-broad"]'),
                          CleanHTML('(//div[@class="group-days-summary"])[1]/div[1]/div/div/div[@class="day-summary-wind"]'),
                          CleanHTML('(//div[@class="group-days-summary"])[1]/div[1]/div/div/div[@class="day-summary-uv"]'),
                          CleanHTML('(//div[@class="group-days-summary"])[1]/div[1]/div/div/div[@class="day-summary-indice"]/img/@title'))

        def obj_temp(self):
            temp = CleanDecimal(Regexp(CleanText('(//div[@class="group-days-summary"])[1]/div[1]/div/div/div[@class="day-summary-temperature"]'),
                                       '(.*)\|.*'))(self)
            unit = Regexp(CleanText('(//div[@class="group-days-summary"])[1]/div[1]/div/div/div[@class="day-summary-temperature"]'),
                          u'.*\xb0(\w) \|.*')(self)
            return Temperature(float(temp), unit)
