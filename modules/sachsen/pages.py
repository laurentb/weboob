# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Florent Fourcot
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

from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import Env, CleanText, Regexp, Field, DateTime, Map
from weboob.browser.filters.html import Attr
from weboob.capabilities.gauge import Gauge, GaugeMeasure, GaugeSensor
from weboob.capabilities.base import NotAvailable, NotLoaded

import re


class ListPage(HTMLPage):

    @method
    class get_rivers_list(ListElement):
        item_xpath = ".//a[@onmouseout='pegelaus()']"

        class item(ItemElement):
            klass = Gauge

            forecasts = {'pf_gerade.png': u'stable',
                         'pf_unten.png':  u'Go down',
                         'pf_oben.png':   u'Go up',
                         }
            alarmlevel = {"as1.gif": u"Alarmstufe 1", "as2.gif": u"Alarmstufe 2",
                          "as3.gif": u"Alarmstufe 3", "as4.gig": u"Alarmstufe 4",
                          "qua_grau.gif": u"No alarm function", "p_gruen.gif": u"",
                          "qua_weiss.gif": u"no data", "as0.gif": u"",
                          "MNW.gif": u""}

            obj_id = CleanText(Env('id'))
            obj_name = CleanText(Env('name'), "'")
            obj_city = Regexp(Field('name'), '^([^\s]+).*')
            obj_object = Env('object')

            def parse(self, el):
                div = el.getparent()
                img = Regexp(Attr('.//img', 'src'), "(.*?)/(.*)", "\\2")(div)
                data = unicode(el.attrib['onmouseover']) \
                    .strip('pegelein(').strip(')').replace(",'", ",").split("',")

                self.env['id'] = data[7].strip()
                self.env['name'] = data[0]
                self.env['object'] = data[1]
                self.env['datetime'] = data[2]
                self.env['levelvalue'] = data[3]
                self.env['flowvalue'] = data[4]
                self.env['forecast'] = data[5]
                self.env['alarm'] = img

            def add_sensor(self, sensors, name, unit, value, forecast, alarm, date):
                sensor = GaugeSensor("%s-%s" % (self.obj.id, name.lower()))
                sensor.name = name
                sensor.unit = unit
                sensor.forecast = forecast
                lastvalue = GaugeMeasure()
                lastvalue.alarm = alarm
                try:
                    lastvalue.level = float(value)
                except ValueError:
                    lastvalue.level = NotAvailable
                lastvalue.date = date
                sensor.lastvalue = lastvalue
                sensor.history = NotLoaded
                sensor.gaugeid = self.obj.id

                sensors.append(sensor)

            def obj_sensors(self):
                sensors = []

                lastdate = DateTime(Regexp(Env('datetime'), r'(\d+)\.(\d+)\.(\d+) (\d+):(\d+)', r'\3-\2-\1 \4:\5', default=NotAvailable), default=NotAvailable)(self)
                forecast = Map(Env('forecast'), self.forecasts, default=NotAvailable)(self)
                alarm = Map(Env('alarm'), self.alarmlevel, default=u'')(self)

                self.add_sensor(sensors, u"Level", u"cm", self.env['levelvalue'], forecast, alarm, lastdate)
                self.add_sensor(sensors, u"Flow", u"m3/s", self.env['flowvalue'], forecast, alarm, lastdate)

                return sensors


class HistoryPage(HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//table[@width="215"]/tr'

        class item(ItemElement):
            klass = GaugeMeasure
            verif = re.compile("\d\d.\d\d.\d+ \d\d:\d\d")

            def condition(self):
                return self.verif.match(self.el[0].text_content())

            obj_date = DateTime(Regexp(CleanText('.'), r'(\d+)\.(\d+)\.(\d+) (\d+):(\d+)', r'\3-\2-\1 \4:\5'))
            sensor_types = [u'Level', u'Flow']

            def obj_level(self):
                index = self.sensor_types.index(self.env['sensor'].name) + 1
                try:
                    return float(self.el[index].text_content())
                except ValueError:
                    return NotAvailable
                # TODO: history.alarm
