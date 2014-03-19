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

from datetime import datetime, date, time
from weboob.tools.browser2.page import HTMLPage, method, ListElement, ItemElement
from weboob.tools.browser2.filters import Env
from weboob.capabilities.gauge import Gauge, GaugeMeasure, GaugeSensor
from weboob.capabilities.base import NotAvailable, NotLoaded

import re

__all__ = ['ListPage', 'HistoryPage']


class ListPage(HTMLPage):

    @method
    class get_rivers_list(ListElement):
        item_xpath = ".//a[@onmouseout='pegelaus()']"

        class item(ItemElement):
            klass = Gauge

            alarmlevel = {"as1.gif": u"Alarmstufe 1", "as2.gif": u"Alarmstufe 2",
                          "as3.gif": u"Alarmstufe 3", "as4.gig": u"Alarmstufe 4",
                          "qua_grau.gif": u"No alarm function", "p_gruen.gif": u"",
                          "qua_weiss.gif": u"no data", "as0.gif": u"",
                          "MNW.gif": u""}

            obj_id = Env('id')
            obj_name = Env('name')
            obj_city = Env('city')
            obj_object = Env('object')
            obj_sensors = Env('sensors')

            def init_sensor(self, _id, name, unit, value, forecast, alarm, date):
                sensor = GaugeSensor("%s-%s" % (_id, name.lower()))
                sensor.name = name
                sensor.unit = unit
                sensor.forecast = forecast
                lastvalue = GaugeMeasure()
                lastvalue.alarm = alarm
                try:
                    lastvalue.level = float(value)
                except:
                    lastvalue.level = NotAvailable
                lastvalue.date = date
                sensor.lastvalue = lastvalue
                sensor.history = NotLoaded
                sensor.gaugeid = unicode(_id)

                return sensor

            def parse(self, el):
                div = el.getparent()
                img = div.find('.//img').attrib['src'].split('/')[1]
                data = el.attrib['onmouseover'] \
                    .strip('pegelein(').strip(')').replace(",'", ",").split("',")

                self.env['id'] = data[7].strip()
                self.env['name'] = unicode(data[0].strip("'"))
                self.env['city'] = self.env['name'].split(' ')[0]
                self.env['object'] = unicode(data[1])

                sensors = []
                try:
                    datenumbers = data[2].split(' ')[0].split(".")
                    timenumbers = data[2].split(' ')[1].split(":")
                    lastdate = date(*reversed([int(x) for x in datenumbers]))
                    lasttime = time(*[int(x) for x in timenumbers])
                    lastdate = datetime.combine(lastdate, lasttime)
                except:
                    lastdate = NotAvailable

                bildforecast = data[5]
                if bildforecast == "pf_gerade.png":
                    forecast = u"stable"
                elif bildforecast == "pf_unten.png":
                    forecast = u"Go down"
                elif bildforecast == "pf_oben.png":
                    forecast = u"Go up"
                else:
                    forecast = NotAvailable

                try:
                    alarm = self.alarmlevel[img]
                except KeyError:
                    alarm = u""

                levelsensor = self.init_sensor(self.env['id'], u"Level",
                                               u"cm", data[3], forecast,
                                               alarm, lastdate)
                sensors.append(levelsensor)

                flowsensor = self.init_sensor(self.env['id'], u"Flow",
                                              u"m3/s", data[4], forecast,
                                              alarm, lastdate)
                sensors.append(flowsensor)

                self.env['sensors'] = sensors


class HistoryPage(HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//table[@width="215"]/tr'

        class item(ItemElement):
            klass = GaugeMeasure
            verif = re.compile("\d\d.\d\d.\d+ \d\d:\d\d")

            obj_date = Env('date')
            obj_level = Env('level')
            obj_id = None

            def condition(self):
                if self.verif.match(self.el[0].text_content()):
                    return True
                return False

            def parse(self, line):
                leveldate = date(*reversed([int(x)
                    for x in line[0].text_content().split(' ')[0].split(".")]))
                leveltime = time(*[int(x)
                    for x in line[0].text_content().split(' ')[1].split(":")])
                self.env['date'] = datetime.combine(leveldate, leveltime)

                if self.env['sensor'].name == u"Level":
                    try:
                        self.env['level'] = float(line[1].text_content())
                    except:
                        self.env['level'] = NotAvailable
                elif self.env['sensor'].name == u"Flow":
                    try:
                        self.env['level'] = float(line[2].text_content())
                    except:
                        self.env['level'] = NotAvailable
                # TODO: history.alarm
