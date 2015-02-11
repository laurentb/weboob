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


class SearchPage(HTMLPage):
    def get_info(self, _id):
        result_id = self.doc.xpath('//table[@id="shipment-details-table"]//tr[position()=1]/td[@id="td-bold"]')
        if not result_id:
            raise ParcelNotFound("No such ID: %s" % _id)
        result_id = result_id[0].text
        if result_id != _id:
            raise ParcelNotFound("ID mismatch: expecting %s, got %s" % (_id, result_id))

        p = Parcel(id)
        events = self.doc.xpath('//div[@id="shipment-event-table-cell"]')
        p.history = [self.build_event(i, div) for i, div in enumerate(events)]
        most_recent = p.history[0]
        p.status, p.info = self.guess_status(p.history)
        p.info = most_recent.activity
        return p

    def guess_status(self, events):
        for event in events:
            txt = event.activity
            if txt == "Itella has received advance information of the item.":
                return Parcel.STATUS_PLANNED, txt
            elif txt == "Item in sorting." or txt == "Item has been registered.":
                return Parcel.STATUS_IN_TRANSIT, txt
            elif txt.startswith("Item ready for pick up") or \
                    txt.startswith("A notice of arrival has been sent to the recipient"):
                return Parcel.STATUS_ARRIVED, txt
        else:
            return Parcel.STATUS_UNKNOWN, events[0].activity

    def build_event(self, index, div):
        event = Event(index)
        event.activity = unicode(div.xpath('div[@class="shipment-event-table-header"]')[0].text)
        event.date = parse_date(div.xpath('.//span[@class="shipment-event-table-label" and text()="Registration:"]/'
                                          'following-sibling::span')[0].text)
        event.location = unicode(div.xpath('.//span[@class="shipment-event-table-label" and text()="Location:"]/'
                                           'following-sibling::span')[0].text)
        return event
