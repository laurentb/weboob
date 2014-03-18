# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon, Florent Fourcot
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

from weboob.tools.browser2.page import HTMLPage, method, ListElement, ItemElement
from weboob.tools.browser2.filters import CleanText, Env, Regexp, Attr
from weboob.capabilities.gauge import GaugeMeasure, GaugeSensor
from weboob.capabilities.base import NotAvailable


__all__ = ['StartPage']


class StartPage(HTMLPage):

    @method
    class get_sensors_list(ListElement):
        item_xpath = '//p[@align="center"]'

        class item(ItemElement):
            klass = GaugeSensor

            obj_name = Regexp(CleanText('.'), '(.*?) {0,}: .*', "\\1")
            obj_id = CleanText(Regexp(Attr('name'), '(.*)', "dd-\\1"), " .():")
            obj_unit = Env('unit')
            obj_lastvalue = Env('lastvalue')
            obj_gaugeid = u"wetter"
            obj_forecast = NotAvailable

            def split_unit(self, text):
                if u"Temperatur" in text:
                    value = text.split(': ')[1].split(u'°')[0]
                    unit = u'°C'
                else:
                    value = text.split(':')[-1].split()[0]
                    unit = text.split(':')[-1].split()[1]
                return value, unit

            def parse(self, el):
                text = CleanText(el)(self)

                level, self.env['unit'] = self.split_unit(text)
                lastvalue = GaugeMeasure()
                lastvalue.level = float(level)
                lastvalue.alarm = NotAvailable
                self.env['lastvalue'] = lastvalue
