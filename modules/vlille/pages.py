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


from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, TableElement, method
from weboob.browser.filters.standard import CleanText, TableCell, DateTime, Field

from weboob.capabilities.gauge import Gauge, GaugeMeasure, GaugeSensor
from weboob.capabilities.base import NotLoaded


class ListStationsPage(HTMLPage):
    @method
    class get_station_list(TableElement):
        item_xpath = "//div[@id='liste-station']/table/tbody/tr"
        head_xpath = "//div[@id='liste-station']/table/thead/tr/th/@class"

        col_id = 'libelle'
        col_name = 'Nom'
        col_city = 'commune'
        col_adresse = 'adresse'
        col_bikes = 'nbVelosDispo'
        col_attachs = 'nbPlacesDispo'

        class item(ItemElement):
            klass = Gauge

            obj_id = CleanText(TableCell('id'))
            obj_name = CleanText(TableCell('name'))
            obj_city = CleanText(TableCell('city'))
            obj_object = u'vLille'

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

            """
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
            """

            def obj_sensors(self):
                sensors = []
                last_update = DateTime(CleanText('(//div[@class="maj"]/b)[1]', replace=[(u'à', '')]))(self)
                adresse = CleanText(TableCell('adresse'))(self)
                sensors.append(self._create_bikes_sensor(CleanText(TableCell('bikes'))(self),
                                                         Field('id')(self),
                                                         last_update, adresse))
                sensors.append(self._create_attach_sensor(CleanText(TableCell('attachs'))(self),
                                                          Field('id')(self),
                                                          last_update, adresse))
                # sensors.append(self._create_status_sensor(CleanText('status')(self),
                #                                          self.env['idgauge'],
                #                                          last_update, adresse))
                return sensors
