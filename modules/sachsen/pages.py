# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Florent Fourcot
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
import lxml.html

from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import Env, CleanText, Regexp, Field, DateTime, Map
from weboob.browser.filters.html import Attr
from weboob.capabilities.gauge import Gauge, GaugeMeasure, GaugeSensor
from weboob.capabilities.base import NotAvailable, NotLoaded

from weboob.exceptions import ParseError

import re


class ListPage(HTMLPage):

    @method
    class get_rivers_list(ListElement):
        item_xpath = ".//div[@class='msWrapper']/script"

        class item(ItemElement):
            klass = Gauge

            extract = re.compile(".*content:(?P<html>.*),show")
            forecasts = {'pfeil_gerade.png.jsf': u'stable',
                         'pfeil_unten.png.jsf':  u'Go down',
                         'pfeil_oben.png.jsf':   u'Go up',
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
                raw = self.extract.match(el.text).group("html")
                raw = raw.replace('\\"', '"').replace('\\n', '').replace('\\/', '/')
                parsed = lxml.html.fromstring(raw)

                self.env['name'] = CleanText('.//span[@class="popUpTitleBold"]')(parsed)
                self.env['object'] = CleanText('.//span[@class="popUpTitleNormal"]')(parsed).strip(' /')
                url = Attr('.//div[@class="popUpMsDiagramm"]/img', 'src')(parsed)
                self.env['id'] = url.split('_')[1]

                for tr in parsed.xpath('.//tr'):
                    td = tr.xpath('.//td')
                    if len(td) == 1 and "Datum" in td[0].text:
                        l = td[0].text.split()[1:3]
                        self.env['datetime'] = "%s %s" % (l[0], l[1])
                    elif len(td) == 2:
                        if "Wasserstand" in td[0].text:
                            self.env['levelvalue'] = td[1].text.split()[0]
                        elif "Durchfluss" in td[0].text:
                            self.env['flowvalue'] = td[1].text.split()[0]
                        elif "Tendenz" in td[0].text:
                            try:
                                self.env['forecast'] = Attr('img', 'src')(td[1]).split("/")[-1]
                            except ParseError:
                                self.env['forecast'] = None
                # TODO
                self.env['alarm'] = None

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
        item_xpath = '//table[@class="quickbarTable"]/tbody/tr'

        class item(ItemElement):
            klass = GaugeMeasure
            verif = re.compile("\d\d.\d\d.\d+ \d\d:\d\d")

            obj_date = DateTime(Regexp(CleanText('.'), r'(\d+)\.(\d+)\.(\d+) (\d+):(\d+)', r'\3-\2-\1 \4:\5'))
            sensor_types = [u'Level', u'Flow']

            def obj_level(self):
                index = self.sensor_types.index(self.env['sensor'].name) + 1
                try:
                    return float(self.el[index].text_content())
                except ValueError:
                    return NotAvailable
                # TODO: history.alarm
