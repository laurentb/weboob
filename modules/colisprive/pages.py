# -*- coding: utf-8 -*-

# Copyright(C) 2014 Florent Fourcot
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

from datetime import date
from weboob.browser.pages import HTMLPage
from weboob.capabilities.parcel import Parcel, Event, ParcelNotFound


def update_status(p, status):
    if p.status < status:
        p.status = status


class TrackPage(HTMLPage):
    def get_info(self, _id):
        p = Parcel(_id)

        statustr = self.doc.xpath('//tr[@class="bandeauText"]')[0]
        status = statustr.xpath('td')[1].text

        p.info = status
        p.status = p.STATUS_UNKNOWN

        p.history = []
        for i, tr in enumerate(self.doc.xpath('//table[@class="tableHistoriqueColis"]//tr[@class="bandeauText"]')):
            tds = tr.findall('td')
            try:
                if tds[0].attrib['class'] != "tdText":
                    continue
            except:
                continue

            ev = Event(i)
            ev.location = None
            ev.activity = tds[1].text
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
            ev.date = date(*reversed([int(x) for x in tds[0].text.split('/')]))
            p.history.append(ev)

        try:
            datelivre = self.doc.xpath('//div[@class="NoInstNoRecla"]')
            clean = datelivre[0].text
            if "Votre colis a déja été livré" in clean:
                p.status = p.STATUS_ARRIVED
        except:
            pass
        return p


class ErrorPage(HTMLPage):
    def get_info(self, _id):
        raise ParcelNotFound("No such ID: %s" % _id)
