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
from weboob.capabilities import NotAvailable
from weboob.deprecated.browser import Page


class IndexPage(Page):
    def track_package(self, _id):
        self.browser.select_form(predicate=lambda form: form.attrs.get('id', '') == 'suivreEnvoi')
        self.browser['chronoNumbers'] = _id.encode('utf-8')
        self.browser.submit()


class TrackPage(Page):
    def get_info(self, id):
        if len(self.document.xpath('//libelle[@nom="MSG_AUCUN_EVT"]')) > 0:
            return None

        p = Parcel(id)
        p.arrival = NotAvailable
        p.history = []

        for i, tr in enumerate(self.document.xpath('//table[@class="tabListeEnvois"]//tr')):
            tds = tr.findall('td')
            if len(tds) < 3:
                continue

            ev = Event(i)
            ev.location = unicode(tds[1].text) if tds[1].text else None
            ev.activity = unicode(tds[1].find('br').tail)
            if tds[-1].text is not None:
                ev.activity += ', ' + self.parser.tocleanstring(tds[-1])
            date = re.sub('[a-z]+', '', self.parser.tocleanstring(tds[0])).strip()
            date = re.sub('(\d+)/(\d+)/(\d+)', r'\3-\2-\1', date)
            ev.date = parse_date(date)
            p.history.append(ev)

        p.info = ' '.join([t.strip() for t in self.document.xpath('//div[@class="numeroColi2"]')[0].itertext()][1:])
        if u'Livraison effectuée' in p.history[0].activity:
            p.status = p.STATUS_ARRIVED

        return p
