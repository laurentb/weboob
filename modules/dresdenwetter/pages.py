# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon, Florent Fourcot
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

from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Field, Filter, debug
from weboob.capabilities.gauge import GaugeMeasure, GaugeSensor
from weboob.capabilities.base import NotAvailable


class Split(Filter):
    def __init__(self, selector, mode):
        super(Split, self).__init__(selector)
        self.mode = mode

    @debug()
    def filter(self, txt):
        if u"Temperatur" in txt:
            value = txt.split(': ')[1].split(u'°')[0]
            unit = u'°C'
        else:
            value = txt.split(':')[-1].split()[0]
            unit = txt.split(':')[-1].split()[1]
            if unit == u"W/m":
                unit = u"W/m²"
        try:
            value = float(value)
        except ValueError:
            value = NotAvailable
        return [value, unit][self.mode]


class StartPage(HTMLPage):

    @method
    class get_sensors_list(ListElement):
        item_xpath = '//p[@align="center"]'

        class item(ItemElement):
            klass = GaugeSensor

            obj_name = Regexp(CleanText('.'), '(.*?) {0,}: .*', "\\1")
            obj_id = CleanText(Regexp(Field('name'), '(.*)', "dd-\\1"), " .():")
            obj_gaugeid = u"wetter"
            obj_forecast = NotAvailable
            obj_unit = Split(CleanText('.'), 1)

            def obj_lastvalue(self):
                lastvalue = GaugeMeasure()
                lastvalue.level = Split(CleanText('.'), 0)(self)
                lastvalue.alarm = NotAvailable
                return lastvalue
