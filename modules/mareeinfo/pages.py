# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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
from weboob.browser.filters.standard import CleanText, DateTime, CleanDecimal, Regexp
from weboob.browser.filters.html import Link, XPath
from weboob.capabilities.gauge import Gauge, GaugeMeasure, GaugeSensor
from datetime import timedelta
import re


class IndexPage(HTMLPage):
    @method
    class get_harbor_list(ListElement):
        item_xpath = "//a[@class='Port PP'] | //a[@class='Port PS']"

        class item(ItemElement):
            klass = Gauge

            obj_id = CleanText(Link('.'), replace=[('/', '')])
            obj_name = CleanText('.')
            obj_city = CleanText('.')
            obj_object = u'Port'

            def validate(self, obj):
                if self.env['pattern']:
                    return self.env['pattern'].lower() in obj.name.lower()
                return True

    @method
    class get_harbor_infos(ItemElement):
        klass = Gauge

        def _create_coef_sensor(self, gauge_id, AM=True):
            name = CleanText('//tr[@class="MJE"]/th[4]')(self)
            _name = 'matin' if AM else 'aprem'
            value = self._get_coef_value(AM=AM)

            if value:
                coef = GaugeSensor(u'%s-%s-%s' % (gauge_id, name, _name))
                coef.name = '%s %s' % (name, _name)
                coef.lastvalue = value
                coef.gaugeid = gauge_id

                coef.history = []
                for jour in range(0, 7):
                    measure = self._get_coef_value(AM=AM, jour=jour)
                    if measure:
                        coef.history.append(measure)

                return coef

        def _get_coef_value(self, AM=True, jour=0):
            if AM:
                time = DateTime(CleanText('//tr[@id="MareeJours_%s"]/td[1]/b[1]' % jour), strict=False)(self)
                value = CleanText('//tr[@id="MareeJours_%s"]/td[3]/b[1]' % jour)(self)
            else:
                time, value = None, None
                if len(XPath('//tr[@id="MareeJours_%s"]/td[1]/b' % jour)(self)) > 1:
                    time = DateTime(CleanText('//tr[@id="MareeJours_%s"]/td[1]/b[2]' % jour), strict=False)(self)
                    value = CleanText('//tr[@id="MareeJours_%s"]/td[3]/b[2]' % jour)(self)

            if time and value:
                measure = GaugeMeasure()
                measure.level = float(value)
                measure.date = time + timedelta(days=jour)
                return measure

        def _create_high_tide(self, gauge_id, AM=True):
            name = CleanText('//tr[@class="MJE"]/th[3]')(self)
            _name = 'matin' if AM else 'aprem'
            value = self._get_high_tide_value(AM=AM)

            if value:
                tide = GaugeSensor(u'%s-%s-PM-%s' % (gauge_id, name, _name))
                tide.name = u'Pleine Mer %s' % (_name)
                tide.unit = u'm'
                tide.lastvalue = value
                tide.gaugeid = gauge_id

                tide.history = []
                for jour in range(0, 7):
                    measure = self._get_high_tide_value(AM=AM, jour=jour)
                    if measure:
                        tide.history.append(measure)

                return tide

        def _get_high_tide_value(self, AM=True, jour=0):
            if AM:
                time = DateTime(CleanText('//tr[@id="MareeJours_%s"]/td[1]/b[1]' % jour), strict=False)(self)
                value = CleanDecimal('//tr[@id="MareeJours_0"]/td[2]/b[1]', replace_dots=True)(self)
            else:
                time, value = None, None
                if len(XPath('//tr[@id="MareeJours_%s"]/td[1]/b' % jour)(self)) > 1:
                    time = DateTime(CleanText('//tr[@id="MareeJours_%s"]/td[1]/b[2]' % jour),
                                    strict=False, default=None)(self)
                    value = CleanDecimal('//tr[@id="MareeJours_0"]/td[2]/b[2]', replace_dots=True,
                                         default=None)(self)

            if time and value:
                measure = GaugeMeasure()
                measure.level = float(value)
                measure.date = time + timedelta(days=jour)
                return measure

        def _create_low_tide(self, gauge_id, AM=True):
            name = CleanText('//tr[@class="MJE"]/th[3]')(self)
            _name = 'matin' if AM else 'aprem'
            value = self._get_low_tide_value(AM=AM)

            if value:
                tide = GaugeSensor(u'%s-%s-BM-%s' % (gauge_id, name, _name))
                tide.name = u'Basse Mer %s' % (_name)
                tide.unit = u'm'
                tide.lastvalue = value
                tide.gaugeid = gauge_id

                tide.history = []
                for jour in range(0, 7):
                    measure = self._get_low_tide_value(AM=AM, jour=jour)
                    if measure:
                        tide.history.append(measure)

                return tide

        def _is_low_tide_first(self, jour):
            return XPath('//tr[@id="MareeJours_%s"]/td[1]' % jour)(self)[0].getchildren()[0].tag != 'b'

        def _get_low_tide_value(self, AM=True, jour=0):
            slow_tide_pos = 1 if self._is_low_tide_first(jour) else 2
            m = re.findall('(\d{2}h\d{2})', CleanText('//tr[@id="MareeJours_%s"]/td[1]' % jour)(self))

            re_time = '(\d{2}h\d{2}).*(\d{2}h\d{2}).*(\d{2}h\d{2})'
            re_value = '(.*)m(.*)m(.*)m'
            if len(m) > 3:
                re_time = '(\d{2}h\d{2}).*(\d{2}h\d{2}).*(\d{2}h\d{2}).*(\d{2}h\d{2})'
                re_value = '(.*)m(.*)m(.*)m(.*)m'

            if AM:
                time = DateTime(Regexp(CleanText('//tr[@id="MareeJours_%s"]/td[1]' % jour),
                                       re_time,
                                       '\\%s' % slow_tide_pos), strict=False)(self)

                value = CleanDecimal(Regexp(CleanText('//tr[@id="MareeJours_%s"]/td[2]' % jour),
                                            re_value,
                                            '\\%s' % slow_tide_pos),
                                     replace_dots=True, default=None)(self)

            else:
                slow_tide_pos += 2
                time, value = None, None
                if len(m) > slow_tide_pos - 1:
                    time = DateTime(Regexp(CleanText('//tr[@id="MareeJours_%s"]/td[1]' % jour),
                                           re_time,
                                           '\\%s' % slow_tide_pos), strict=False)(self)

                    value = CleanDecimal(Regexp(CleanText('//tr[@id="MareeJours_%s"]/td[2]' % jour),
                                                re_value,
                                                '\\%s' % slow_tide_pos),
                                         replace_dots=True, default=None)(self)

            if time and value:
                measure = GaugeMeasure()
                measure.level = float(value)
                measure.date = time + timedelta(days=jour)
                return measure

        def obj_sensors(self):
            sensors = []
            high_tide_PM = self._create_high_tide(self.obj.id)
            if high_tide_PM:
                sensors.append(high_tide_PM)
            high_tide_AM = self._create_high_tide(self.obj.id, AM=False)
            if high_tide_AM:
                sensors.append(high_tide_AM)
            low_tide_AM = self._create_low_tide(self.obj.id)
            if low_tide_AM:
                sensors.append(low_tide_AM)
            low_tide_PM = self._create_low_tide(self.obj.id, AM=False)
            if low_tide_PM:
                sensors.append(low_tide_PM)
            coef_AM = self._create_coef_sensor(self.obj.id)
            if coef_AM:
                sensors.append(coef_AM)
            coef_PM = self._create_coef_sensor(self.obj.id, AM=False)
            if coef_PM:
                sensors.append(coef_PM)
            return sensors
