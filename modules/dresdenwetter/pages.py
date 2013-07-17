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

from weboob.tools.browser import BasePage
from weboob.capabilities.gauge import GaugeMeasure, GaugeSensor
from weboob.capabilities.base import NotAvailable


__all__ = ['StartPage']


class StartPage(BasePage):
    name = [u"Temperatur", u"Wind", u"Luftdruck", u"Luftfeuchtigkeit",
            u"Niederschlag", u"Globalstrahlung"]
    unit = [u"°C", u"km/h", u"hPa", u"%", u"mm", u"W/m²"]

    def get_sensors_list(self):
        paraphs = self.document.xpath('//p[@align="center"]')
        sensors = []
        for i in range(len(paraphs)):
            sensor = GaugeSensor("dd-%s" % self.name[i].lower())
            sensor.name = self.name[i]
            sensor.unit = self.unit[i]
            sensor.forecast = NotAvailable
            sensor.history = NotAvailable
            sensor.gaugeid = u"private-dresden"
            paraph = paraphs[i]
            lastvalue = GaugeMeasure()
            lastvalue.alarm = NotAvailable
            if i == 0:
                text = paraph.xpath('b/span/font[@size="4"]')[1].text
                lastvalue.level = float(text.split('\n')[1].split(u'°')[0])
            if i == 1:
                text = paraph.xpath('b/span/font')[2].text
                lastvalue.level = float(text.split('\n')[1])
            if i == 2:
                text = paraph.xpath('span/font/b')[0].text
                lastvalue.level = float(text.split('\n')[2].split('hPa')[0])
            if i == 3:
                text = paraph.xpath('span/font[@size="4"]/b')[0].text
                lastvalue.level = float(text.split('\n')[2].split(u'%')[0]
                        .split(':')[1])
            if i == 4:
                text = paraph.xpath('b/font[@size="4"]/span')[0].text
                lastvalue.level = float(text.split('\n')[0])
            if i == 5:
                text = paraph.xpath('b/font/span')[0].text
                lastvalue.level = float(text.split('\n')[1])
            sensor.lastvalue = lastvalue
            sensors.append(sensor)
        return sensors
