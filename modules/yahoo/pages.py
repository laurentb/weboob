
# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Cedric Defortis
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

from weboob.browser.pages import JsonPage
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.capabilities.weather import Forecast, Current, City, Temperature
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanText, CleanDecimal, Format, Date, Env


class YahooPage(JsonPage):
    @method
    class iter_cities(DictElement):
        item_xpath = 'query/results/place'

        class item(ItemElement):
            klass = City

            obj_id = Dict('woeid')
            obj_name = Format(u'%s, %s, %s', Dict('name'), Dict('admin1/content'), Dict('country/content'))

    @method
    class get_current(ItemElement):
        klass = Current

        def parse(self, el):
            self.env['pct'] = u'%'

        obj_id = Date(Dict('query/results/channel/item/condition/date'))
        obj_date = Date(Dict('query/results/channel/item/condition/date'))
        obj_text = Format('%s - wind: %s%s - humidity:%s%s',
                          Dict('query/results/channel/item/condition/text'),
                          Dict('query/results/channel/wind/speed'),
                          Dict('query/results/channel/units/speed'),
                          Dict('query/results/channel/atmosphere/humidity'),
                          Env('pct'))

        def obj_temp(self):
            temp = CleanDecimal(Dict('query/results/channel/item/condition/temp'))(self)
            unit = CleanText(Dict('query/results/channel/units/temperature'))(self)
            return Temperature(float(temp), unit)

    @method
    class iter_forecast(DictElement):
        item_xpath = 'query/results/channel/item/forecast'

        def parse(self, el):
            self.env['unit'] = Dict('query/results/channel/units/temperature')(el)

        class item(ItemElement):
            klass = Forecast

            obj_id = Dict('date')
            obj_date = Date(Dict('date'))
            obj_text = Dict('text')

            def obj_low(self):
                temp = CleanDecimal(Dict('low'))(self)
                return Temperature(float(temp), Env('unit')(self))

            def obj_high(self):
                temp = CleanDecimal(Dict('high'))(self)
                return Temperature(float(temp), Env('unit')(self))
