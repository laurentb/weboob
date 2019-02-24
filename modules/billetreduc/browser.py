# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

from datetime import datetime, timedelta

from weboob.browser import PagesBrowser, URL

from .pages import ResultsPage, EventPage, EventDatesPage, SearchPage


class BilletreducBrowser(PagesBrowser):
    BASEURL = 'https://www.billetreduc.com'

    search = URL(r'/recherche.htm', SearchPage)
    results = URL(r'/search.htm', ResultsPage)
    event = URL(r'/(?P<id>\d+)/evt.htm', EventPage)
    event_dates = URL(r'/(?P<id>\d+)/evtbook.htm',
                      r'https://www.billetreduc.com/(?P<id>\d+)/evtbook.htm',
                      EventDatesPage)
    book = URL(r'/evtBook.htm\?idevt=(?P<id>\d+)&dh=(?P<ymd>\d+-\d+-\d+)\+(?P<hm>\d+:\d+)')

    def set_id_end(self, event):
        event.id = '%s.%s' % (event.siteid, event.start_date.strftime('%Y-%m-%d.%H:%M'))
        event.end_date = event.start_date + timedelta(seconds=3600)

    def search_events(self, q):
        original_start = q.start_date or datetime.now()

        q = q.copy()
        start = q.start_date or datetime.now()
        start = start.replace(second=0, microsecond=0)

        end = q.end_date or start + timedelta(days=7)

        for date in iter_days(start, end):
            q.start_date = date

            self.search.go()
            self.page.search(q)
            for event in self.page.iter_events(date=date):
                for h, m in event._date_hours:
                    event = event.copy()
                    event.start_date = event.start_date.replace(hour=h, minute=m)
                    self.set_id_end(event)

                    if event.start_date >= original_start:
                        yield event

    def get_event(self, _id):
        try:
            eid, ymd, hm = _id.split('.')
        except ValueError:
            return self.get_event_first(_id)
        else:
            return self.get_event_by_date(eid, ymd, hm)

    def get_event_first(self, eid):
        self.event.go(id=eid)
        event = self.page.get_event()

        self.event_dates.go(id=eid)
        self.page.get_first(event)
        self.set_id_end(event)
        return event

    def get_event_by_date(self, eid, ymd, hm):
        self.event.go(id=eid)
        event = self.page.get_event()
        s = '%sT%s' % (ymd, hm)
        event.start_date = datetime.strptime(s, '%Y-%m-%dT%H:%M')
        event.end_date = event.start_date + timedelta(seconds=3600)

        self.event_dates.go(id=eid)
        self.page.fetch_by_date(event, ymd, hm)
        self.set_id_end(event)
        return event


def iter_days(start_date, end_date):
    while start_date < end_date:
        yield start_date
        start_date += timedelta(days=1)
