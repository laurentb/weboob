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
from weboob.browser.pages import JsonPage
from weboob.capabilities.parcel import Parcel, Event

STATUSES = {
    "DELIVEREDPS": Parcel.STATUS_ARRIVED,
    "DELIVERED": Parcel.STATUS_ARRIVED,
}


class SearchPage(JsonPage):
    def get_info(self, _id):
        p = Parcel(_id)
        events = self.doc["tuStatus"][0]["history"]
        p.history = [self.build_event(i, tr) for i, tr in enumerate(events)]
        p.status = self.guess_status(self.doc["tuStatus"][0]["progressBar"]["statusInfo"])
        p.info = self.doc["tuStatus"][0]["progressBar"]["statusText"]
        return p

    def guess_status(self, code):
        return STATUSES.get(code, Parcel.STATUS_UNKNOWN)

    def build_event(self, index, data):
        event = Event(index)
        date = "%s %s" % (data["date"], data["time"])
        event.date = parse_date(date, dayfirst=False)
        event.location = ", ".join(
            [unicode(data["address"][field]) for field in ["city", "countryName"] if data["address"][field]])
        event.activity = unicode(data["evtDscr"])
        return event
