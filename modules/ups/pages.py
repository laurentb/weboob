# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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


import re
from dateutil.parser import parse as parse_date

from weboob.capabilities.parcel import Parcel, Event
from weboob.deprecated.browser import Page


class TrackPage(Page):
    def get_info(self, id):
        if len(self.parser.tocleanstring(self.document.xpath('//p[@class="error"]')[0])) > 0:
            return None

        p = Parcel(id)
        for dl in self.document.xpath('//dl'):
            dt = dl.find('dt')
            dd = dl.find('dd')
            if dt is None or dd is None:
                continue
            label = self.parser.tocleanstring(dt)
            if label == 'Scheduled Delivery:':
                p.status = p.STATUS_IN_TRANSIT
            elif label == u'Delivered On:':
                p.status = p.STATUS_ARRIVED
            else:
                continue

            m = re.search('(\d+/\d+/\d+)', dd.text)
            if m:
                p.arrival = parse_date(m.group(1))

        p.history = []
        for i, tr in enumerate(self.document.xpath('//table[@class="dataTable"]//tr')):
            tds = tr.findall('td')
            if len(tds) < 4:
                continue

            ev = Event(i)
            ev.location = self.parser.tocleanstring(tds[0])
            ev.activity = self.parser.tocleanstring(tds[-1])
            ev.date = parse_date('%s %s' % (tds[1].text, tds[2].text))
            p.history.append(ev)

        p.info = self.document.xpath('//a[@id="tt_spStatus"]')[0].text.strip()

        return p
