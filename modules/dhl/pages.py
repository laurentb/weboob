# -*- coding: utf-8 -*-

# Copyright(C) 2015      Matthieu Weber
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

from dateutil.parser import parse as parse_date

from weboob.browser.pages import HTMLPage
from weboob.capabilities.parcel import Parcel, Event, ParcelNotFound

# Based on http://www.parcelok.com/delivery-status-dhl.html
STATUSES = {
    "The instruction data for this shipment have been provided by the sender to DHL "
    "electronically": Parcel.STATUS_PLANNED,
    "The shipment has been posted by the sender at the retail outlet": Parcel.STATUS_PLANNED,

    "The shipment has been processed in the destination parcel center": Parcel.STATUS_IN_TRANSIT,
    "The international shipment has been processed in the parcel center of origin": Parcel.STATUS_IN_TRANSIT,
    "The international shipment has been processed in the export parcel center": Parcel.STATUS_IN_TRANSIT,
    "The shipment will be transported to the destination country and, from there, handed over to "
    "the delivery organization.": Parcel.STATUS_IN_TRANSIT,
    "The shipment has arrived in the destination country": Parcel.STATUS_IN_TRANSIT,
    "The shipment has arrived at the parcel center.": Parcel.STATUS_IN_TRANSIT,
    "Shipment is prepared for customs clearance in country of destination": Parcel.STATUS_IN_TRANSIT,
    "The shipment is being prepared for delivery in the delivery depot": Parcel.STATUS_IN_TRANSIT,
    "Scheduled for delivery": Parcel.STATUS_IN_TRANSIT,
    "The shipment has been loaded onto the delivery vehicle": Parcel.STATUS_IN_TRANSIT,
    "Shipment has arrived at delivery location": Parcel.STATUS_IN_TRANSIT,
    "With delivery courier": Parcel.STATUS_IN_TRANSIT,
    "Delivery attempted; consignee premises closed": Parcel.STATUS_IN_TRANSIT,
    "The shipment has been damaged and is being returned to the parcel center for"
    "repackaging": Parcel.STATUS_IN_TRANSIT,

    "The shipment has been successfully delivered": Parcel.STATUS_ARRIVED,
}


class SearchPage(HTMLPage):
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
        p.status, p.info = self.guess_status(p.history[-1])
        return p

    def guess_status(self, most_recent):
        txt = most_recent.activity
        return STATUSES.get(txt, Parcel.STATUS_UNKNOWN), txt

    def build_event(self, index, tr):
        event = Event(index)
        event.date = parse_date(tr.xpath('./td[1]')[0].text.strip(), dayfirst=True, fuzzy=True)
        event.location = unicode(tr.xpath('./td[2]')[0].text.strip())
        event.activity = unicode(tr.xpath('./td[3]')[0].text.strip())
        return event
