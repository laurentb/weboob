# -*- coding: utf-8 -*-

# Copyright(C) 2015      Matthieu Weber
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

from dateutil.parser import parse as parse_date

from weboob.tools.compat import unicode
from weboob.browser.pages import JsonPage, HTMLPage
from weboob.capabilities.parcel import Parcel, Event, ParcelNotFound


class DHLExpressSearchPage(JsonPage):
    # Based on http://www.dhl.com/etc/designs/dhl/docroot/tracking/less/tracking.css
    STATUSES = {
        u'105': Parcel.STATUS_PLANNED,
        u'104': Parcel.STATUS_PLANNED,
        u'102': Parcel.STATUS_IN_TRANSIT,
        u'101': Parcel.STATUS_ARRIVED,
    }

    def get_info(self, _id):
        if u'errors' in self.doc:
            raise ParcelNotFound("No such ID: %s" % _id)
        elif u'results' in self.doc:
            result = self.doc[u'results'][0]
            p = Parcel(_id)
            p.history = [self.build_event(e) for e in result[u'checkpoints']]
            p.status = self.STATUSES.get(result[u'delivery'][u'code'], Parcel.STATUS_UNKNOWN)
            p.info = p.history[0].activity
            return p
        else:
            raise ParcelNotFound("Unexpected reply from server")

    def build_event(self, e):
        index = e[u'counter']
        event = Event(index)
        event.date = parse_date(e[u'date'] + " " + e.get(u'time', ''), dayfirst=True, fuzzy=True)
        event.location = e.get(u'location', '')
        event.activity = e[u'description']
        return event


class DeutschePostDHLSearchPage(HTMLPage):
    # Based on http://www.parcelok.com/delivery-status-dhl.html
    STATUSES = {
        "Order data sent to DHL electronically": Parcel.STATUS_PLANNED,
        "International shipment": Parcel.STATUS_IN_TRANSIT,
        "Processing in parcel center": Parcel.STATUS_IN_TRANSIT,
        "Delivery": Parcel.STATUS_IN_TRANSIT,
        "Shipment has been successfully delivered": Parcel.STATUS_ARRIVED,
    }

    def get_info(self, _id):
        result_id = self.doc.xpath('//th[@class="mm_sendungsnummer"]')
        if not result_id:
            raise ParcelNotFound("No such ID: %s" % _id)
        result_id = result_id[0].text
        if result_id != _id:
            raise ParcelNotFound("ID mismatch: expecting %s, got %s" % (_id, result_id))

        p = Parcel(_id)
        events = self.doc.xpath('//div[@class="accordion-inner"]/table/tbody/tr')
        p.history = [self.build_event(i, tr) for i, tr in enumerate(events)]
        status_msgs = self.doc.xpath('//tr[@class="mm_mailing_process "]//img[contains(@src, "ACTIVE")]/@alt')
        if len(status_msgs) > 0:
            p.status = self.STATUSES.get(status_msgs[-1], Parcel.STATUS_UNKNOWN)
        else:
            p.status = Parcel.STATUS_UNKNOWN
        p.info = p.history[-1].activity
        return p

    def build_event(self, index, tr):
        event = Event(index)
        event.date = parse_date(tr.xpath('./td[1]')[0].text.strip(), dayfirst=True, fuzzy=True)
        event.location = unicode(tr.xpath('./td[2]')[0].text_content().strip())
        event.activity = unicode(tr.xpath('./td[3]')[0].text_content().strip())
        return event
