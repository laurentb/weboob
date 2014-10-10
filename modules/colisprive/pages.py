# -*- coding: utf-8 -*-

# Copyright(C) 2014 Florent Fourcot
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

from datetime import date
from weboob.deprecated.browser import Page
from weboob.capabilities.parcel import Parcel, Event


def update_status(p, status):
    if p.status < status:
        p.status = status


class TrackPage(Page):
    def get_info(self, _id):
        p = Parcel(_id)

        statustr = self.document.xpath('//tr[@class="bandeauText"]')[0]
        status = self.parser.tocleanstring(statustr.xpath('td')[1])

        p.info = status
        p.status = p.STATUS_UNKNOWN

        p.history = []
        for i, tr in enumerate(self.document.xpath('//div[@class="mainbloc4Evt"]//tr')):
            tds = tr.findall('td')
            try:
                if tds[0].attrib['class'] != "titrestatutdate2":
                    continue
            except:
                continue

            ev = Event(i)
            ev.location = None
            ev.activity = self.parser.tocleanstring(tds[1])
            if u"Votre colis a été expédié par votre webmarchand" in ev.activity:
                update_status(p, p.STATUS_PLANNED)
            elif u"Votre colis est pris en charge par Colis Privé" in ev.activity:
                update_status(p, p.STATUS_IN_TRANSIT)
            elif u"Votre colis est arrivé sur notre agence régionale" in ev.activity:
                update_status(p, p.STATUS_IN_TRANSIT)
            elif u"Votre colis est en cours de livraison" in ev.activity:
                update_status(p, p.STATUS_IN_TRANSIT)
            elif u"Votre colis a été livré" in ev.activity:
                update_status(p, p.STATUS_ARRIVED)
            ev.date = date(*reversed([int(x) for x in self.parser.tocleanstring(tds[0]).split('/')]))
            p.history.append(ev)

        try:
            datelivre = self.document.xpath('//div[@class="NoInstNoRecla"]')
            clean = self.parser.tocleanstring(datelivre[0])
            if "Votre colis a déja été livré" in clean:
                p.status = p.STATUS_ARRIVED
        except:
            pass
        return p


class ErrorPage(Page):
    pass
