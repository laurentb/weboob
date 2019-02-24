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

from weboob.browser.pages import JsonPage
from weboob.capabilities.parcel import Parcel, Event, ParcelNotFound


class SearchPage(JsonPage):
    STATUSES = {
            "WAITING": Parcel.STATUS_PLANNED,
            "IN_TRANSPORT": Parcel.STATUS_IN_TRANSIT,
            "READY_FOR_PICKUP": Parcel.STATUS_ARRIVED,
            "DELIVERED": Parcel.STATUS_ARRIVED,
            }
    def get_info(self, _id):
        shipments = self.doc["shipments"]
        if not shipments:
            raise ParcelNotFound("No such ID: %s" % _id)
        shipment = shipments[0]
        result_id = shipment["trackingCode"]
        if result_id != _id:
            raise ParcelNotFound("ID mismatch: expecting %s, got %s" % (_id, result_id))

        p = Parcel(_id)
        if shipment["estimatedDeliveryTime"]:
            p.arrival = parse_date(shipment["estimatedDeliveryTime"], ignoretz=True)
        events = shipment["events"]
        p.history = [self.build_event(i, data) for i, data in enumerate(events)]
        p.status = self.STATUSES.get(shipment["phase"], Parcel.STATUS_UNKNOWN)
        most_recent = p.history[0]
        p.info = most_recent.activity
        return p

    def build_event(self, index, data):
        event = Event(index)
        event.activity = data["description"]["en"]
        event.date = parse_date(data["timestamp"], ignoretz=True)
        event.location = data["locationName"]
        return event
