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

STATUSES = {
    1: Parcel.STATUS_PLANNED,
    2: Parcel.STATUS_IN_TRANSIT,
    3: Parcel.STATUS_IN_TRANSIT,
    4: Parcel.STATUS_IN_TRANSIT,
    5: Parcel.STATUS_ARRIVED,
}


class SearchPage(JsonPage):
    def build_doc(self, text):
        from weboob.tools.json import json
        return json.loads(text[1:-1])

    def get_info(self, _id):
        result_id = self.doc.get("TrackingStatusJSON", {}).get("shipmentInfo", {}).get("parcelNumber", None)
        if not result_id:
            raise ParcelNotFound("No such ID: %s" % _id)
        if not _id.startswith(result_id):
            raise ParcelNotFound("ID mismatch: expecting %s, got %s" % (_id, result_id))

        p = Parcel(_id)
        events = self.doc.get("TrackingStatusJSON", {}).get("statusInfos", [])
        p.history = [self.build_event(i, data) for i, data in enumerate(events)]
        p.status = self.guess_status(
            self.doc.get("TrackingStatusJSON", {}).
            get("shipmentInfo", {}).
            get("deliveryStatus"))
        p.info = p.history[-1].activity
        return p

    def guess_status(self, status_code):
        return STATUSES.get(status_code, Parcel.STATUS_UNKNOWN)

    def build_event(self, index, data):
        event = Event(index)
        date = "%s %s" % (data["date"], data["time"])
        event.date = parse_date(date, dayfirst=False)
        event.location = unicode(data["city"])
        event.activity = unicode(", ".join([_["label"] for _ in data["contents"]]))
        return event
