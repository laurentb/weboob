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

from weboob.browser.pages import JsonPage
from weboob.capabilities.parcel import Parcel, Event, ParcelNotFound

# Based on http://www.dhl.com/etc/designs/dhl/docroot/tracking/less/tracking.css
STATUSES = {
    u'105': Parcel.STATUS_PLANNED,
    u'104': Parcel.STATUS_PLANNED,
    u'102': Parcel.STATUS_IN_TRANSIT,
    u'101': Parcel.STATUS_ARRIVED,
}


class SearchPage(JsonPage):
    def get_info(self, _id):
        if u'errors' in self.doc:
            raise ParcelNotFound("No such ID: %s" % _id)
        elif u'results' in self.doc:
            result = self.doc[u'results'][0]
            p = Parcel(_id)
            p.history = [self.build_event(e) for e in result[u'checkpoints']]
            p.status = STATUSES.get(result[u'delivery'][u'code'], Parcel.STATUS_UNKNOWN)
            p.info = p.history[0].activity
            return p
        else:
            raise ParcelNotFound("Unexpected reply from server")

    def build_event(self, e):
        index = e[u'counter']
        event = Event(index)
        event.date = parse_date(e[u'date'] + " " + e.get(u'time',''), dayfirst=True, fuzzy=True)
        event.location = e.get(u'location', '')
        event.activity = e[u'description']
        return event
