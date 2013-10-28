# -*- coding: utf-8 -*-

# Copyright(C) 2013      dud
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
from weboob.capabilities.gauge import Gauge, GaugeMeasure, GaugeSensor
from weboob.capabilities.base import NotLoaded
import datetime
import re

__all__ = ['InfoStationPage', 'ListStationsPage']

AdresseStation = {}


class InfoStationPage(BasePage):
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

    def _get_last_update(self, last_update):
        return datetime.datetime.now() - datetime.timedelta(seconds=int(re.match(r'\d+', last_update).group(0)))

    def get_station_infos(self, gauge_id):
        sensors = []

        last_update = datetime.datetime.fromtimestamp(float(self.parser.select(self.document.getroot(), 'updated', 1).text))
        adresse = AdresseStation[gauge_id]

        sensors.append(self._create_bikes_sensor(self.parser.select(self.document.getroot(), 'available', 1).text, gauge_id, last_update, adresse))
        sensors.append(self._create_attach_sensor(self.parser.select(self.document.getroot(), 'free', 1).text, gauge_id, last_update, adresse))
        sensors.append(self._create_status_sensor(self.parser.select(self.document.getroot(), 'open', 1).text, gauge_id, last_update, adresse))

        return sensors


class ListStationsPage(BasePage):
    def get_station_list(self):
        gauges = []
        for marker in self.parser.select(self.document.getroot(), 'marker'):
            gauge = Gauge(int(marker.get('number')))
            gauge.name = unicode(marker.get('address')).rsplit('-', 1)[0]
            full_address = re.search(r'\d\d\d\d\d.*', unicode(marker.get('fulladdress')))
            if full_address:
                gauge.city = full_address.group()
            gauge.object = u'velib'
            gauges.append(gauge)
            AdresseStation[marker.get('number')] = marker.get('fulladdress')
        return gauges
