# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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


from weboob.browser.pages import HTMLPage, XMLPage
from weboob.browser.elements import ListElement, ItemElement, TableElement, method
from weboob.browser.filters.standard import CleanText, Filter
from weboob.browser.filters.html import TableCell

from weboob.capabilities.gauge import Gauge, GaugeMeasure, GaugeSensor
from weboob.capabilities.base import NotLoaded
import datetime
import re


class LastDateFilter(Filter):
    def filter(self, last_update):
        return datetime.datetime.now() - datetime.timedelta(seconds=int(re.match(r'\d+', last_update).group(0)))


class InfoStationPage(XMLPage):

    ENCODING = 'utf-8'

    @method
    class get_station_infos(ListElement):
        item_xpath = "."

        class item(ItemElement):
            klass = Gauge

            def _create_bikes_sensor(self, value, gauge_id, last_update, adresse):
                levelbikes = GaugeSensor(gauge_id + '-bikes')
                levelbikes.name = u'Bikes'
                levelbikes.address = u'%s' % adresse
                lastvalue = GaugeMeasure()
                lastvalue.level = float(value)
                lastvalue.date = last_update
                if lastvalue.level < 1:
                    lastvalue.alarm = u'Empty station'
                levelbikes.lastvalue = lastvalue
                levelbikes.history = NotLoaded
                levelbikes.gaugeid = gauge_id
                return levelbikes

            def _create_attach_sensor(self, value, gauge_id, last_update, adresse):
                levelattach = GaugeSensor(gauge_id + '-attach')
                levelattach.name = u'Attach'
                levelattach.address = u'%s' % adresse
                lastvalue = GaugeMeasure()
                if lastvalue.level < 1:
                    lastvalue.alarm = u'Full station'
                lastvalue.level = float(value)
                lastvalue.date = last_update
                levelattach.lastvalue = lastvalue
                levelattach.history = NotLoaded
                levelattach.gaugeid = gauge_id
                return levelattach

            def _create_status_sensor(self, value, gauge_id, last_update, adresse):
                levelstatus = GaugeSensor(gauge_id + '-status')
                levelstatus.name = u'Status'
                levelstatus.address = u'%s' % adresse
                lastvalue = GaugeMeasure()
                status = float(value)
                if status == 0:
                    status = 1
                else:
                    status = -1
                if lastvalue.level < 1:
                    lastvalue.alarm = u'Not available station'
                lastvalue.level = float(status)
                lastvalue.date = last_update
                levelstatus.lastvalue = lastvalue
                levelstatus.history = NotLoaded
                levelstatus.gaugeid = gauge_id
                return levelstatus

            def parse(self, el):
                self.obj = self.env['obj']

            def obj_sensors(self):
                sensors = []
                last_update = LastDateFilter(CleanText('lastupd'))(self)
                adresse = CleanText('adress')(self)
                sensors.append(self._create_bikes_sensor(CleanText('bikes')(self),
                                                         self.env['idgauge'],
                                                         last_update, adresse))
                sensors.append(self._create_attach_sensor(CleanText('attachs')(self),
                                                          self.env['idgauge'],
                                                          last_update, adresse))
                sensors.append(self._create_status_sensor(CleanText('status')(self),
                                                          self.env['idgauge'],
                                                          last_update, adresse))
                return sensors


class ListStationsPage(HTMLPage):
    @method
    class get_station_list(TableElement):
        item_xpath = "//table[@id='ctl00_Contenu_ListeStations1_ListViewStations_itemPlaceholderContainer']/tr"
        head_xpath = "//table[@id='ctl00_Contenu_ListeStations1_ListViewStations_itemPlaceholderContainer']/tr/th/@id"

        col_id = 'ctl00_Contenu_ListeStations1_ListViewStations_Th1'
        col_name = 'ctl00_Contenu_ListeStations1_ListViewStations_Th2'
        col_city = 'ctl00_Contenu_ListeStations1_ListViewStations_Th9'

        class item(ItemElement):
            klass = Gauge
            condition = lambda self: (len(self.el.xpath('td/span')) > 4 and not ('id' in self.el.attrib))

            obj_id = CleanText(TableCell('id'))
            obj_name = CleanText(TableCell('name'))
            obj_city = CleanText(TableCell('city'))
            obj_object = u'vLille'
