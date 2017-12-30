
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
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.capabilities.weather import Forecast, Current, City, Temperature
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Format, Eval


class SearchCitiesPage(JsonPage):
    @method
    class iter_cities(DictElement):
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
        item_xpath = '//div[@class="liste-jours"]/ul/li'

        class item(ItemElement):
            klass = Forecast

            obj_id = CleanText('./dl/dt')

            def obj_date(self):
                actual_day_number = Eval(int,
                                         Regexp(CleanText('./dl/dt'),
                                                '\w{3} (\d+)'))(self)
                base_date = date.today()
                if base_date.day > actual_day_number:
                    base_date = base_date.replace(
                        month=(
                            (base_date.month + 1) % 12
                        )
                    )
                base_date = base_date.replace(day=actual_day_number)
                return base_date

            def obj_low(self):
                temp = CleanDecimal(Regexp(CleanText('./dl/dd/span[@class="min-temp"]'),
                                           u'(\d*)\xb0\w Minimale.*'))(self)
                unit = Regexp(CleanText('./dl/dd/span[@class="min-temp"]'), u'.*\xb0(\w) Minimale.*')(self)
                return Temperature(float(temp), unit)

            def obj_high(self):
                temp = CleanDecimal(Regexp(CleanText('./dl/dd/span[@class="max-temp"]'),
                                           u'(.*)\xb0\w Maximale.*'))(self)
                unit = Regexp(CleanText('./dl/dd/span[@class="max-temp"]'), u'.*\xb0(\w) Maximale.*')(self)
                return Temperature(float(temp), unit)

            obj_text = CleanText('./@title')

    @method
    class get_current(ItemElement):
        klass = Current

        obj_id = date.today()
        obj_date = date.today()
        obj_text = Format('%s - %s - %s - Vent %s',
                          CleanText('//ul[@class="prevision-horaire "]/li[@class=" active "]/div/ul/li[@class="day-summary-tress-start"]'),
                          CleanText('//ul[@class="prevision-horaire "]/li[@class=" active "]/div/ul/li[@class="day-summary-image"]'),
                          CleanText('//ul[@class="prevision-horaire "]/li[@class=" active "]/div/ul/li[@class="day-summary-uv"]'),
                          CleanText('//ul[@class="prevision-horaire "]/li[@class=" active "]/div/ul/li[@class="day-summary-wind"]'))

        def obj_temp(self):
            temp = CleanDecimal('//ul[@class="prevision-horaire "]/li[@class=" active "]/ul/li[@class="day-summary-temperature"]')(self)
            unit = Regexp(CleanText('//ul[@class="prevision-horaire "]/li[@class=" active "]/ul/li[@class="day-summary-temperature"]'),
                          u'.*\xb0(\w)')(self)
            return Temperature(float(temp), unit)
